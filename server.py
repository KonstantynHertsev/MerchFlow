"""
FastAPI backend — auth + pipeline.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Request, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from pydantic import BaseModel

import auth
import database
import email_sender

ADMIN_EMAIL             = os.getenv("ADMIN_EMAIL", "")
PADDLE_WEBHOOK_SECRET   = os.getenv("PADDLE_WEBHOOK_SECRET", "")
PADDLE_CLIENT_TOKEN     = os.getenv("PADDLE_CLIENT_TOKEN", "")
PADDLE_PRICE_ID         = os.getenv("PADDLE_PRICE_ID", "")
from ai_vision import get_listing_from_image
from tm_check import check_listing
from csv_writer import build_output, FORMATS

database.init_db()

app = FastAPI()
bearer = HTTPBearer(auto_error=False)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
BATCH_DIR = Path(tempfile.gettempdir()) / "merch_batches"
BATCH_TTL = 3600  # 1 hour


def _cleanup_old_batches():
    if not BATCH_DIR.exists():
        return
    cutoff = time.time() - BATCH_TTL
    for p in BATCH_DIR.iterdir():
        if p.is_dir() and p.stat().st_mtime < cutoff:
            shutil.rmtree(p, ignore_errors=True)


def _save_batch(batch_id: str, images: list[Path]):
    batch_path = BATCH_DIR / batch_id
    batch_path.mkdir(parents=True, exist_ok=True)
    for img in images:
        shutil.copy2(img, batch_path / img.name)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = auth.decode_token(creds.credentials)
        user = database.get_user_by_id(int(payload["sub"]))
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class AuthBody(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register")
def register(body: AuthBody):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if database.get_user_by_email(body.email):
        raise HTTPException(400, "Email already registered")
    hashed = auth.hash_password(body.password)
    user_id = database.create_user(body.email, hashed)
    token = auth.create_token(user_id, body.email)
    try:
        email_sender.send_welcome_email(body.email)
    except Exception as e:
        print(f"[email] {e}")
    return {"token": token, "email": body.email}


@app.post("/api/auth/login")
def login(body: AuthBody):
    user = database.get_user_by_email(body.email)
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = auth.create_token(user["id"], user["email"])
    return {"token": token, "email": user["email"]}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    month  = _current_month()
    is_pro = user["tier"] == "pro"
    used   = 0 if is_pro else database.get_usage(user["id"], month)
    return {
        "id":        user["id"],
        "email":     user["email"],
        "tier":      user["tier"],
        "usage":     used,
        "limit":     None if is_pro else database.FREE_LIMIT,
        "remaining": None if is_pro else max(0, database.FREE_LIMIT - used),
    }


def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    if user["email"] != ADMIN_EMAIL:
        raise HTTPException(403, "Forbidden")
    return user


@app.get("/api/admin/waitlist")
def admin_waitlist(user: dict = Depends(get_admin_user)):
    return database.get_waitlist()


@app.get("/api/admin/users")
def admin_users(user: dict = Depends(get_admin_user)):
    month = _current_month()
    users = database.get_all_users()
    for u in users:
        if u["usage_month"] != month:
            u["usage_count"] = 0
    return users


class ForgotPasswordBody(BaseModel):
    email: str

class ResetPasswordBody(BaseModel):
    token: str
    password: str


@app.post("/api/auth/forgot-password")
def forgot_password(body: ForgotPasswordBody):
    user = database.get_user_by_email(body.email)
    if user:
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        database.create_reset_token(user["id"], token, expires_at)
        try:
            email_sender.send_reset_email(user["email"], token)
        except Exception as e:
            print(f"[email] {e}")
    # Always return ok — prevents email enumeration
    return {"ok": True}


@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordBody):
    record = database.get_reset_token(body.token)
    if not record:
        raise HTTPException(400, "Invalid or expired reset link")
    expires_at = datetime.fromisoformat(record["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(400, "Reset link has expired")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    new_hash = auth.hash_password(body.password)
    if not database.use_reset_token(body.token, new_hash):
        raise HTTPException(400, "Invalid or expired reset link")
    return {"ok": True}


@app.get("/api/config")
def get_config():
    return {
        "paddle_client_token": PADDLE_CLIENT_TOKEN,
        "paddle_price_id":     PADDLE_PRICE_ID,
    }


@app.post("/api/paddle/webhook")
async def paddle_webhook(request: Request):
    body = await request.body()

    if PADDLE_WEBHOOK_SECRET:
        sig_header = request.headers.get("Paddle-Signature", "")
        parts = dict(p.split("=", 1) for p in sig_header.split(";") if "=" in p)
        ts = parts.get("ts", "")
        h1 = parts.get("h1", "")
        signed = f"{ts}:{body.decode()}"
        expected = hmac.new(
            PADDLE_WEBHOOK_SECRET.encode(),
            signed.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, h1):
            raise HTTPException(400, "Invalid signature")

    payload = json.loads(body)
    event_type = payload.get("event_type", "")
    data = payload.get("data", {})

    if event_type == "subscription.activated":
        custom_data = data.get("custom_data") or {}
        user_id = custom_data.get("user_id")
        sub_id = data.get("id", "")
        if user_id:
            database.set_user_tier(int(user_id), "pro", sub_id)

    elif event_type in ("subscription.cancelled", "subscription.paused"):
        sub_id = data.get("id", "")
        if sub_id:
            database.set_user_tier_by_subscription(sub_id, "free")

    elif event_type == "subscription.resumed":
        sub_id = data.get("id", "")
        if sub_id:
            database.set_user_tier_by_subscription(sub_id, "pro")

    return {"ok": True}


class WaitlistBody(BaseModel):
    email: str

@app.post("/api/waitlist")
def waitlist(body: WaitlistBody):
    added = database.add_to_waitlist(body.email)
    return {"added": added}


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _extract_images(upload: UploadFile, tmp_dir: Path) -> list[Path]:
    suffix = Path(upload.filename).suffix.lower()
    images = []

    if suffix == ".zip":
        zip_path = tmp_dir / "upload.zip"
        zip_path.write_bytes(upload.file.read())
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                p = Path(name)
                if p.name.startswith("._") or "__MACOSX" in p.parts:
                    continue
                if p.suffix.lower() in ALLOWED_EXTENSIONS:
                    zf.extract(name, tmp_dir / "images")
                    images.append(tmp_dir / "images" / name)
    elif suffix in ALLOWED_EXTENSIONS:
        img_path = tmp_dir / upload.filename
        img_path.write_bytes(upload.file.read())
        images.append(img_path)
    else:
        raise HTTPException(400, "Upload a ZIP archive or a PNG/JPG image.")

    return images


@app.post("/api/process")
async def process(
    file:       Annotated[UploadFile, File()],
    brand:      Annotated[str, Form()] = "Independent Artist",
    price:      Annotated[str, Form()] = "19.99",
    colors:     Annotated[str, Form()] = "Black,Navy,Dark Heather,Asphalt",
    department: Annotated[str, Form()] = "mens",
    software:   Annotated[str, Form()] = "lazy_merch",
    user:       dict = Depends(get_current_user),
):
    if software not in FORMATS:
        raise HTTPException(400, f"Unknown software: {software}")

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        images = _extract_images(file, tmp_dir)
        if not images:
            raise HTTPException(400, "No valid images found.")

        batch_id = str(uuid.uuid4())
        _cleanup_old_batches()
        _save_batch(batch_id, images)

        # Check usage limit
        month     = _current_month()
        used      = database.get_usage(user["id"], month)
        remaining = database.FREE_LIMIT - used
        if user["tier"] == "free" and remaining <= 0:
            raise HTTPException(402, "Monthly limit reached")
        if user["tier"] == "free" and len(images) > remaining:
            images = images[:remaining]

        profile = {
            "brand":      brand,
            "price":      price,
            "colors":     [c.strip() for c in colors.split(",") if c.strip()],
            "department": department,
        }

        async def process_one(img_path: Path) -> dict:
            try:
                listing = await asyncio.to_thread(get_listing_from_image, img_path)
                tm = check_listing(listing)
                listing["_tm_flagged"] = tm.flagged
                listing["_tm_hits"]    = tm.hits
                listing["_profile"]    = profile
                listing["_error"]      = None
                return listing
            except Exception as e:
                return {
                    "_image_file": img_path.name,
                    "_error":      str(e),
                    "_tm_flagged": False,
                    "_tm_hits":    [],
                }

        results = await asyncio.gather(*[process_one(p) for p in images])

        # Increment usage by successful images only
        processed = sum(1 for r in results if not r.get("_error"))
        if processed:
            database.increment_usage(user["id"], month, processed)

        file_bytes, file_ext = build_output(results, profile, software)
        csv_b64 = base64.b64encode(file_bytes).decode()

        new_used = used + processed

        return JSONResponse({
            "listings": [
                {
                    "image":       r.get("_image_file", ""),
                    "title":       r.get("title", ""),
                    "brand":       r.get("_profile", {}).get("brand", ""),
                    "bullet_1":    r.get("bullet_1", ""),
                    "bullet_2":    r.get("bullet_2", ""),
                    "bullet_3":    r.get("bullet_3", ""),
                    "description": r.get("description", ""),
                    "keywords":    r.get("keywords", ""),
                    "tm_flagged":  r.get("_tm_flagged", False),
                    "tm_hits":     r.get("_tm_hits", []),
                    "truncated":   r.get("_truncated", []),
                    "error":       r.get("_error"),
                }
                for r in results
            ],
            "csv_b64":   csv_b64,
            "file_ext":  file_ext,
            "software":  software,
            "batch_id":  batch_id,
            "usage":     new_used,
            "limit":     database.FREE_LIMIT,
            "remaining": max(0, database.FREE_LIMIT - new_used),
        })
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class FeedbackBody(BaseModel):
    rating: int
    comment: str = ""


@app.post("/api/feedback")
def submit_feedback(body: FeedbackBody, user: dict = Depends(get_current_user)):
    if not 1 <= body.rating <= 5:
        raise HTTPException(400, "Rating must be 1–5")
    database.add_feedback(user["id"], user["email"], body.rating, body.comment.strip())
    return {"ok": True}


@app.get("/api/admin/feedback")
def admin_feedback(user: dict = Depends(get_admin_user)):
    return database.get_all_feedback()


class RegenerateBody(BaseModel):
    batch_id: str
    image_file: str
    fields: list[str]  # any of: "title", "bullets", "description"


@app.post("/api/regenerate")
async def regenerate(body: RegenerateBody, user: dict = Depends(get_current_user)):
    img_path = BATCH_DIR / body.batch_id / body.image_file
    if not img_path.exists():
        raise HTTPException(404, "Image not found — batch may have expired (1 hour limit)")

    listing = await asyncio.to_thread(get_listing_from_image, img_path)
    tm = check_listing(listing)

    result: dict = {"tm_flagged": tm.flagged, "tm_hits": tm.hits}
    if "title" in body.fields:
        result["title"] = listing.get("title", "")
    if "bullets" in body.fields:
        result["bullet_1"] = listing.get("bullet_1", "")
        result["bullet_2"] = listing.get("bullet_2", "")
        result["bullet_3"] = listing.get("bullet_3", "")
    if "description" in body.fields:
        result["description"] = listing.get("description", "")

    return result


class ExportBody(BaseModel):
    listings: list[dict]
    profile: dict
    software: str


@app.post("/api/export")
def export_file(body: ExportBody, user: dict = Depends(get_current_user)):
    internal = [
        {
            "_image_file": l.get("image", ""),
            "title":       l.get("title", ""),
            "bullet_1":    l.get("bullet_1", ""),
            "bullet_2":    l.get("bullet_2", ""),
            "bullet_3":    l.get("bullet_3", ""),
            "bullet_4":    l.get("bullet_4", ""),
            "bullet_5":    l.get("bullet_5", ""),
            "description": l.get("description", ""),
            "keywords":    l.get("keywords", ""),
        }
        for l in body.listings if not l.get("error")
    ]
    profile = body.profile
    if isinstance(profile.get("colors"), str):
        profile["colors"] = [c.strip() for c in profile["colors"].split(",") if c.strip()]
    file_bytes, file_ext = build_output(internal, profile, body.software)
    return {
        "file_b64": base64.b64encode(file_bytes).decode(),
        "file_ext": file_ext,
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")
