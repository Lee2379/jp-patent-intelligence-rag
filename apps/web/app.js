const queryInput = document.querySelector("#query");
const askButton = document.querySelector("#askButton");
const workspace = document.querySelector("#workspace");
const loading = document.querySelector("#loading");
const errorPanel = document.querySelector("#errorPanel");
const sourceDialog = document.querySelector("#sourceDialog");
let currentSources = [];
let currentAuditId = null;
const sessionId = crypto.randomUUID();
const navItems = document.querySelectorAll(".nav-item");

function setActiveNav(hash) {
  navItems.forEach((item) => {
    const href = item.getAttribute("href");
    if (href?.startsWith("#")) item.classList.toggle("active", href === hash);
  });
}

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

function renderAnswer(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(/\[S(\d+)\]/g, (_, number) =>
    `<button class="citation" data-source="${Number(number) - 1}">S${number}</button>`
  );
}

function sourceCard(source) {
  const preview = source.text.replace(/\s+/g, " ");
  return `<button class="source-card" data-source="${source.rank - 1}">
    <div class="source-top"><span class="source-id">${escapeHtml(source.source_id)}</span><span class="source-score">RRF ${source.score.toFixed(4)}</span></div>
    <h3>JP ${escapeHtml(source.document_id)}</h3>
    <div class="source-meta">${source.year} / ${escapeHtml(source.section)}</div>
    <p>${escapeHtml(preview)}</p>
    <div class="source-footer"><span>BM25 ${source.sparse_score ?? "—"}</span><span>DENSE ${source.dense_score ?? "—"}</span><span>View source</span></div>
  </button>`;
}

function openSource(index) {
  const source = currentSources[index];
  if (!source) return;
  document.querySelector("#dialogContent").innerHTML = `<div class="dialog-inner">
    <span class="source-id">${escapeHtml(source.source_id)}</span>
    <h3>JP ${escapeHtml(source.document_id)}</h3>
    <div class="source-meta">${source.year} · ${escapeHtml(source.section)} · 公開特許公報</div>
    <pre>${escapeHtml(source.text)}</pre>
    <div class="path">SOURCE PATH<br>${escapeHtml(source.local_path)}</div>
  </div>`;
  sourceDialog.showModal();
}

async function runAnalysis() {
  const query = queryInput.value.trim();
  if (query.length < 2) {
    queryInput.focus();
    return;
  }
  askButton.disabled = true;
  workspace.classList.add("hidden");
  errorPanel.classList.add("hidden");
  loading.classList.remove("hidden");
  try {
    const year = document.querySelector("#year").value;
    const section = document.querySelector("#section").value;
    const payload = {
      query,
      answer_language: document.querySelector("#language").value,
      top_k: 4,
      actor_id: document.querySelector("#actorId").value.trim() || "analyst-01",
      session_id: sessionId,
      require_review: true,
    };
    if (year) payload.years = [Number(year)];
    if (section) payload.sections = [section];
    const response = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${response.status}`);
    }
    const data = await response.json();
    currentSources = data.sources;
    currentAuditId = data.audit_id;
    document.querySelector("#answerBody").innerHTML = renderAnswer(data.answer);
    const gateLabel = data.evidence_assessment.accepted ? "EVIDENCE PASS" : "EVIDENCE INSUFFICIENT";
    document.querySelector("#answerMode").textContent = `${gateLabel} · ${data.mode.replaceAll("_", " ").toUpperCase()}`;
    document.querySelector("#modelName").textContent = data.model === "none" ? "RETRIEVAL ONLY" : data.model;
    document.querySelector("#reviewStatus").textContent = `REVIEW / ${data.review_status.toUpperCase()}`;
    document.querySelector("#timing").textContent = `RETRIEVAL ${Math.round(data.retrieval_ms)} MS / TOTAL ${(data.total_ms / 1000).toFixed(1)} S`;
    document.querySelector("#disclaimer").textContent = data.disclaimer;
    document.querySelector("#sourceCount").textContent = `${data.sources.length} PASSAGES / ${new Set(data.sources.map((item) => item.document_id)).size} PATENTS`;
    document.querySelector("#sourceGrid").innerHTML = data.sources.map(sourceCard).join("");
    document.querySelector("#auditReceipt").textContent = `${data.audit_id} / ${data.audit_hash}`;
    document.querySelector("#reviewNotes").value = "";
    document.querySelector("#reviewResult").textContent = "";
    document.querySelectorAll("[data-decision]").forEach((button) => { button.disabled = false; });
    document.querySelector("#reviewPanel").classList.toggle("hidden", data.review_status === "not_required");
    loading.classList.add("hidden");
    workspace.classList.remove("hidden");
    workspace.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    loading.classList.add("hidden");
    errorPanel.classList.remove("hidden");
    document.querySelector("#errorText").textContent = error.message;
  } finally {
    askButton.disabled = false;
  }
}

async function loadStatus() {
  try {
    const [healthResponse, statsResponse] = await Promise.all([fetch("/api/health"), fetch("/api/stats")]);
    const health = await healthResponse.json();
    const stats = await statsResponse.json();
    const status = document.querySelector("#systemStatus");
    status.textContent = health.status === "ready" ? "● READY" : health.retrieval_ready ? "● RETRIEVAL READY" : "○ INDEX REQUIRED";
    status.style.color = health.retrieval_ready ? "var(--success)" : "var(--warning)";
    const auditStatus = document.querySelector("#auditStatus");
    auditStatus.textContent = health.audit?.chain_valid ? `✓ AUDIT ${health.audit.events}` : "! AUDIT WARNING";
    auditStatus.style.color = health.audit?.chain_valid ? "var(--success)" : "var(--warning)";
    if (stats.data.documents_written) {
      const documentCount = stats.data.documents_written.toLocaleString();
      document.querySelector("#documentCount").textContent = documentCount;
      document.querySelector("#sidebarDocumentCount").textContent = documentCount;
    }
    if (stats.index.documents) document.querySelector("#aiDocumentCount").textContent = stats.index.documents.toLocaleString();
  } catch (_) {
    document.querySelector("#systemStatus").textContent = "○ OFFLINE";
    document.querySelector("#auditStatus").textContent = "○ AUDIT OFFLINE";
  }
}

async function submitReview(decision) {
  if (!currentAuditId) return;
  const buttons = document.querySelectorAll("[data-decision]");
  buttons.forEach((button) => { button.disabled = true; });
  const result = document.querySelector("#reviewResult");
  result.textContent = "RECORDING REVIEW…";
  try {
    const response = await fetch("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answer_audit_id: currentAuditId,
        reviewer_id: document.querySelector("#reviewerId").value.trim() || "reviewer-01",
        decision,
        notes: document.querySelector("#reviewNotes").value.trim(),
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${response.status}`);
    }
    const data = await response.json();
    document.querySelector("#reviewStatus").textContent = `REVIEW / ${data.review_status.toUpperCase()}`;
    result.textContent = `${data.review_status.toUpperCase()} · CHAIN ${data.chain_valid ? "VALID" : "FAILED"} · ${data.review_audit_id}`;
  } catch (error) {
    result.textContent = `REVIEW FAILED · ${error.message}`;
    buttons.forEach((button) => { button.disabled = false; });
  }
}

queryInput.addEventListener("input", () => {
  document.querySelector("#characterCount").textContent = `${queryInput.value.length} / 500`;
});
queryInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runAnalysis();
});
askButton.addEventListener("click", runAnalysis);
document.querySelectorAll("[data-query]").forEach((button) => button.addEventListener("click", () => {
  queryInput.value = button.dataset.query;
  queryInput.dispatchEvent(new Event("input"));
  queryInput.focus();
}));
document.body.addEventListener("click", (event) => {
  const sourceButton = event.target.closest("[data-source]");
  if (sourceButton && !sourceButton.dataset.query) openSource(Number(sourceButton.dataset.source));
});
document.querySelector("#dialogClose").addEventListener("click", () => sourceDialog.close());
document.querySelectorAll("[data-decision]").forEach((button) => button.addEventListener("click", () => submitReview(button.dataset.decision)));
sourceDialog.addEventListener("click", (event) => {
  if (event.target === sourceDialog) sourceDialog.close();
});
navItems.forEach((item) => {
  const href = item.getAttribute("href");
  if (href?.startsWith("#")) item.addEventListener("click", () => setActiveNav(href));
});
window.addEventListener("hashchange", () => setActiveNav(window.location.hash || "#research"));
setActiveNav(window.location.hash || "#research");
loadStatus();
