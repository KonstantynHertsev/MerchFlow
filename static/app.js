let selectedFile = null;
let csvB64 = null;
let fileExt = "csv";
let currentSoftware = "lazy_merch";
let currentBatchId = null;
let allListings = [];
let currentProfile = {};

// --- Auth guard ---
function getToken() { return localStorage.getItem("mf_token"); }

function logout() {
  localStorage.removeItem("mf_token");
  localStorage.removeItem("mf_email");
  location.href = "/auth.html";
}

// Redirect to login if no token
if (!getToken()) location.href = "/auth.html";

// --- Profile defaults ---
const DEFAULT_PROFILE = {
  name: "Default",
  brand: "Independent Artist",
  price: "19.99",
  colors: "Black,Navy,Dark Heather,Asphalt",
  department: "mens",
};

// --- Profile storage ---
function getProfiles() {
  try { return JSON.parse(localStorage.getItem("merch_profiles") || "{}"); }
  catch { return {}; }
}

function saveProfiles(profiles) {
  localStorage.setItem("merch_profiles", JSON.stringify(profiles));
}

function getActiveProfileName() {
  return localStorage.getItem("merch_active_profile") || DEFAULT_PROFILE.name;
}

function setActiveProfileName(name) {
  localStorage.setItem("merch_active_profile", name);
}

function readFields() {
  return {
    brand:      document.getElementById("brand").value,
    price:      document.getElementById("price").value,
    colors:     document.getElementById("colors").value,
    department: document.getElementById("department").value,
  };
}

function applyFields(data) {
  document.getElementById("brand").value      = data.brand      ?? DEFAULT_PROFILE.brand;
  document.getElementById("price").value      = data.price      ?? DEFAULT_PROFILE.price;
  document.getElementById("colors").value     = data.colors     ?? DEFAULT_PROFILE.colors;
  document.getElementById("department").value = data.department ?? DEFAULT_PROFILE.department;
}

function rebuildSelect(activeName) {
  const sel = document.getElementById("profile-select");
  const profiles = getProfiles();
  const names = [DEFAULT_PROFILE.name, ...Object.keys(profiles).filter(n => n !== DEFAULT_PROFILE.name)];

  sel.innerHTML = names.map(n =>
    `<option value="${esc(n)}" ${n === activeName ? "selected" : ""}>${esc(n)}</option>`
  ).join("");
}

function loadProfile() {
  const name = document.getElementById("profile-select").value;
  setActiveProfileName(name);

  if (name === DEFAULT_PROFILE.name) {
    applyFields(DEFAULT_PROFILE);
  } else {
    const profiles = getProfiles();
    if (profiles[name]) applyFields(profiles[name]);
  }
  autoSaveCurrentFields();
}

function saveProfile() {
  const currentName = document.getElementById("profile-select").value;
  const isDefault = currentName === DEFAULT_PROFILE.name;

  const name = prompt(
    "Profile name:",
    isDefault ? "" : currentName
  );
  if (!name || !name.trim()) return;
  const trimmed = name.trim();
  if (trimmed === DEFAULT_PROFILE.name) {
    alert(`"${DEFAULT_PROFILE.name}" is reserved and cannot be used.`);
    return;
  }

  const profiles = getProfiles();
  profiles[trimmed] = { name: trimmed, ...readFields() };
  saveProfiles(profiles);
  setActiveProfileName(trimmed);
  rebuildSelect(trimmed);
}

function deleteProfile() {
  const name = document.getElementById("profile-select").value;
  if (name === DEFAULT_PROFILE.name) {
    alert("The default profile cannot be deleted.");
    return;
  }
  if (!confirm(`Delete profile "${name}"?`)) return;

  const profiles = getProfiles();
  delete profiles[name];
  saveProfiles(profiles);
  setActiveProfileName(DEFAULT_PROFILE.name);
  rebuildSelect(DEFAULT_PROFILE.name);
  applyFields(DEFAULT_PROFILE);
}

// Auto-save current field values under the active profile name
function autoSaveCurrentFields() {
  const name = getActiveProfileName();
  if (name === DEFAULT_PROFILE.name) return; // don't overwrite default
  const profiles = getProfiles();
  if (profiles[name]) {
    profiles[name] = { name, ...readFields() };
    saveProfiles(profiles);
  }
}

// --- Init on page load ---
document.addEventListener("DOMContentLoaded", () => {
  const activeName = getActiveProfileName();
  rebuildSelect(activeName);

  if (activeName === DEFAULT_PROFILE.name) {
    applyFields(DEFAULT_PROFILE);
  } else {
    const profiles = getProfiles();
    applyFields(profiles[activeName] ?? DEFAULT_PROFILE);
  }

  // Show email in header + load usage
  document.getElementById("user-email").textContent = localStorage.getItem("mf_email") || "";
  loadUsage();

  // Auto-save on any field change
  ["brand", "price", "colors", "department"].forEach(id => {
    document.getElementById(id).addEventListener("change", autoSaveCurrentFields);
  });
});

// --- Usage ---
async function loadUsage() {
  try {
    const res = await fetch("/api/auth/me", {
      headers: { "Authorization": "Bearer " + getToken() },
    });
    if (res.status === 401) { logout(); return; }
    const data = await res.json();
    updateUsageBadge(data.usage, data.limit);
  } catch {}
}

function updateUsageBadge(used, limit) {
  const badge = document.getElementById("usage-badge");
  const remaining = limit - used;
  badge.textContent = `${used} / ${limit} images`;
  badge.className = "usage-badge" + (remaining === 0 ? " full" : remaining <= 10 ? " warning" : "");
  if (remaining === 0) {
    document.getElementById("run-btn").disabled = true;
    showLimitModal();
  }
}

function showLimitModal() {
  document.getElementById("limit-modal").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("limit-modal").classList.add("hidden");
}

async function submitWaitlist(e) {
  e.preventDefault();
  const btn   = document.getElementById("waitlist-btn");
  const email = document.getElementById("waitlist-email").value;
  btn.disabled = true; btn.textContent = "Joining…";
  try {
    await fetch("/api/waitlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    document.querySelector(".waitlist-form").classList.add("hidden");
    document.getElementById("waitlist-success").classList.remove("hidden");
  } finally {
    btn.disabled = false; btn.textContent = "Join Waitlist";
  }
}

// --- Drag & drop ---
const zone = document.getElementById("upload-zone");
const fileInput = document.getElementById("file-input");

zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag-over"); });
zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
zone.addEventListener("drop", e => {
  e.preventDefault();
  zone.classList.remove("drag-over");
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
zone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(f) {
  selectedFile = f;
  const el = document.getElementById("file-name");
  el.textContent = `📎 ${f.name}  (${(f.size / 1024).toFixed(0)} KB)`;
  el.classList.remove("hidden");
  document.getElementById("run-btn").disabled = false;
}

// --- Pipeline ---
async function runPipeline() {
  if (!selectedFile) return;

  setProgress(true, 20, "Uploading file...");

  const software = document.querySelector('input[name="software"]:checked')?.value || "lazy_merch";

  const form = new FormData();
  form.append("file",       selectedFile);
  form.append("brand",      document.getElementById("brand").value);
  form.append("price",      document.getElementById("price").value);
  form.append("colors",     document.getElementById("colors").value);
  form.append("department", document.getElementById("department").value);
  form.append("software",   software);

  setProgress(true, 45, "AI is analyzing images...");

  let data;
  try {
    const resp = await fetch("/api/process", {
      method: "POST",
      headers: { "Authorization": "Bearer " + getToken() },
      body: form,
    });
    if (resp.status === 401) { logout(); return; }
    if (resp.status === 402) { setProgress(false); showLimitModal(); return; }
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Ошибка сервера");
    }
    data = await resp.json();
  } catch (e) {
    setProgress(false);
    alert("Error: " + e.message);
    return;
  }

  setProgress(true, 90, "Building file...");
  csvB64 = data.csv_b64;
  fileExt = data.file_ext || "csv";
  currentSoftware = data.software || "lazy_merch";
  currentBatchId = data.batch_id || null;
  allListings = data.listings || [];
  currentProfile = {
    brand:      document.getElementById("brand").value,
    price:      document.getElementById("price").value,
    colors:     document.getElementById("colors").value,
    department: document.getElementById("department").value,
  };
  renderResults(allListings);
  setProgress(false);
  if (data.usage !== undefined) updateUsageBadge(data.usage, data.limit);
  if (data.remaining === 0) showLimitModal();
}

function setProgress(show, pct = 0, label = "") {
  const card = document.getElementById("progress-card");
  const runBtn = document.getElementById("run-btn");

  if (show) {
    card.classList.remove("hidden");
    document.getElementById("results-card").classList.add("hidden");
    runBtn.disabled = true;
    document.getElementById("progress-fill").style.width = pct + "%";
    document.getElementById("progress-label").textContent = label;
  } else {
    card.classList.add("hidden");
    runBtn.disabled = false;
  }
}

function renderResults(listings) {
  const card = document.getElementById("results-card");
  const list = document.getElementById("listings-list");
  const warnBlock = document.getElementById("warnings-block");
  const countEl = document.getElementById("results-count");

  const anyFlagged   = listings.some(l => l.tm_flagged);
  const anyTruncated = listings.some(l => l.truncated && l.truncated.length > 0);
  warnBlock.classList.toggle("hidden", !anyFlagged);
  document.getElementById("truncated-block").classList.toggle("hidden", !anyTruncated);

  countEl.textContent = `(${listings.length})`;
  list.innerHTML = "";

  listings.forEach((l, idx) => {
    const div = document.createElement("div");
    div.className = "listing-item" + (l.error ? " error" : l.tm_flagged ? " flagged" : "");
    div.dataset.idx = idx;
    div.dataset.image = l.image;

    if (l.error) {
      div.innerHTML = `
        <div class="listing-top">
          <div>
            <div class="listing-filename">${esc(l.image)}</div>
            <div class="listing-title">Processing error</div>
          </div>
          <span class="badge badge-error">✗ Error</span>
        </div>
        <div class="error-msg">${esc(l.error)}</div>`;
    } else {
      div.innerHTML = listingHTML(l, idx);
    }

    list.appendChild(div);
  });

  card.classList.remove("hidden");
}

function listingHTML(l, idx) {
  const bullets = [l.bullet_1, l.bullet_2, l.bullet_3]
    .filter(Boolean)
    .map(b => `<div class="bullet">${esc(b)}</div>`)
    .join("");
  const badge = l.tm_flagged
    ? `<span class="badge badge-warn">⚠ TM: ${esc(l.tm_hits.join(", "))}</span>`
    : `<span class="badge badge-ok">✓ Clean</span>`;
  return `
    <div class="listing-top">
      <div>
        <div class="listing-filename">${esc(l.image)}</div>
        <div class="listing-title">${esc(l.title)}</div>
      </div>
      ${badge}
    </div>
    <div class="listing-bullets">${bullets}</div>
    <div class="listing-desc">${esc(l.description)}</div>
    <div class="regen-bar">
      <button class="btn-regen-toggle" onclick="toggleRegenPanel(this)">↻ Regenerate</button>
      <div class="regen-panel hidden">
        <label class="regen-check"><input type="checkbox" value="title" checked> Title</label>
        <label class="regen-check"><input type="checkbox" value="bullets"> Bullets</label>
        <label class="regen-check"><input type="checkbox" value="description"> Description</label>
        <button class="btn-regen-go" onclick="doRegenerate(this, ${idx})">Go</button>
      </div>
    </div>`;
}

function toggleRegenPanel(btn) {
  const panel = btn.nextElementSibling;
  panel.classList.toggle("hidden");
}

async function doRegenerate(btn, idx) {
  if (!currentBatchId) return;
  const listing = allListings[idx];
  if (!listing) return;

  const bar = btn.closest(".regen-bar");
  const checks = bar.querySelectorAll("input[type=checkbox]:checked");
  const fields = Array.from(checks).map(c => c.value);
  if (!fields.length) return;

  btn.disabled = true;
  btn.textContent = "…";

  try {
    const res = await fetch("/api/regenerate", {
      method: "POST",
      headers: { "Authorization": "Bearer " + getToken(), "Content-Type": "application/json" },
      body: JSON.stringify({ batch_id: currentBatchId, image_file: listing.image, fields }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Regeneration failed");
      return;
    }
    const data = await res.json();

    // Merge updated fields into allListings
    Object.assign(allListings[idx], data);

    // Re-render just this card
    const card = document.querySelector(`.listing-item[data-idx="${idx}"]`);
    if (card) {
      card.className = "listing-item" + (allListings[idx].tm_flagged ? " flagged" : "");
      card.innerHTML = listingHTML(allListings[idx], idx);
    }

    // Rebuild XLSX in background
    rebuildExport();
  } finally {
    btn.disabled = false;
    btn.textContent = "Go";
  }
}

async function rebuildExport() {
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Authorization": "Bearer " + getToken(), "Content-Type": "application/json" },
      body: JSON.stringify({ listings: allListings, profile: currentProfile, software: currentSoftware }),
    });
    if (!res.ok) return;
    const data = await res.json();
    csvB64 = data.file_b64;
    fileExt = data.file_ext;
  } catch {}
}

function downloadCSV() {
  if (!csvB64) return;
  const bytes = Uint8Array.from(atob(csvB64), c => c.charCodeAt(0));
  const mime = fileExt === "xlsx"
    ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    : "text/csv;charset=utf-8;";
  const blob = new Blob([bytes], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const nameMap = { lazy_merch: "LazyMerch", flying_upload: "FlyingUpload", merch_titans: "MerchTitans" };
  const softLabel = nameMap[currentSoftware] || currentSoftware;
  a.download = `MerchFlow_${softLabel}.${fileExt}`;
  a.click();
  URL.revokeObjectURL(url);
}

// --- Feedback ---
let feedbackRating = 0;

function openFeedback() {
  feedbackRating = 0;
  document.getElementById("feedback-comment").value = "";
  document.getElementById("feedback-error").style.display = "none";
  document.getElementById("feedback-success").style.display = "none";
  updateStars(0);
  document.getElementById("feedback-modal").classList.remove("hidden");
}

function closeFeedback() {
  document.getElementById("feedback-modal").classList.add("hidden");
}

function setRating(val) {
  feedbackRating = val;
  updateStars(val);
}

function updateStars(val) {
  document.querySelectorAll(".star").forEach(s => {
    s.classList.toggle("active", parseInt(s.dataset.v) <= val);
  });
}

async function submitFeedback() {
  const errEl = document.getElementById("feedback-error");
  const okEl  = document.getElementById("feedback-success");
  errEl.style.display = "none";
  okEl.style.display  = "none";

  if (!feedbackRating) { errEl.textContent = "Please select a rating."; errEl.style.display = "block"; return; }

  const comment = document.getElementById("feedback-comment").value.trim();
  const res = await fetch("/api/feedback", {
    method: "POST",
    headers: { "Authorization": "Bearer " + getToken(), "Content-Type": "application/json" },
    body: JSON.stringify({ rating: feedbackRating, comment }),
  });

  if (res.ok) {
    okEl.style.display = "block";
    setTimeout(closeFeedback, 1500);
  } else {
    errEl.textContent = "Something went wrong. Try again.";
    errEl.style.display = "block";
  }
}

function esc(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
