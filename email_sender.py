import os
import resend


def _send(to_email: str, subject: str, html: str, text: str):
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not set in .env")
    resend.api_key = api_key
    resend.Emails.send({
        "from":    os.getenv("FROM_EMAIL", "MerchFlow <onboarding@resend.dev>"),
        "to":      [to_email],
        "subject": subject,
        "html":    html,
        "text":    text,
    })


def send_welcome_email(to_email: str):
    text = (
        "Hey, welcome to MerchFlow!\n\n"
        "You can now upload your designs and generate Amazon Merch listings in seconds.\n\n"
        "Your free plan includes 50 images per month.\n\n"
        f"Get started: {os.getenv("APP_URL", "http://localhost:8000")}\n\n"
        "— The MerchFlow Team"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#e2e8f0;background:#0f172a">
  <h2 style="color:#818cf8;margin-bottom:8px">⚡ Welcome to MerchFlow!</h2>
  <p>You're all set. Upload your designs and get Amazon Merch listings generated in seconds.</p>
  <ul style="color:#cbd5e1;line-height:1.8">
    <li>Upload a ZIP with your images</li>
    <li>Get titles, bullets, and descriptions instantly</li>
    <li>Export to your upload tool of choice</li>
  </ul>
  <p style="margin-bottom:24px">Your free plan includes <strong>50 images per month</strong>.</p>
  <a href="{os.getenv("APP_URL", "http://localhost:8000")}"
     style="display:inline-block;background:#6366f1;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">
    Start Uploading
  </a>
  <p style="color:#64748b;font-size:13px;margin-top:28px">— The MerchFlow Team</p>
</body></html>"""
    _send(to_email, "Welcome to MerchFlow ⚡", html, text)


def send_reset_email(to_email: str, token: str):
    reset_url = f"{os.getenv("APP_URL", "http://localhost:8000")}/auth.html?reset={token}"
    text = (
        f"You requested a password reset for your MerchFlow account.\n\n"
        f"Reset link (expires in 1 hour):\n{reset_url}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#e2e8f0;background:#0f172a">
  <h2 style="color:#818cf8;margin-bottom:8px">⚡ MerchFlow</h2>
  <p style="margin-bottom:24px">You requested a password reset. Click the button below — the link expires in <strong>1 hour</strong>.</p>
  <a href="{reset_url}"
     style="display:inline-block;background:#6366f1;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">
    Reset Password
  </a>
  <p style="color:#64748b;font-size:13px;margin-top:28px">
    If you didn't request this, you can safely ignore this email.<br>
    Or copy this link: {reset_url}
  </p>
</body></html>"""
    _send(to_email, "MerchFlow — Reset your password", html, text)
