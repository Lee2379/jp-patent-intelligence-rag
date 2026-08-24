const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

let auditEvents = [];
const eventDialog = document.querySelector("#eventDialog");

function eventSummary(event) {
  if (event.event_type === "review_decision") {
    return `${event.payload.decision.toUpperCase()} · ${event.payload.notes || "no note"}`;
  }
  return event.payload.query || event.event_type;
}

function eventRow(event, index) {
  return `<button class="audit-row" data-event-index="${index}">
    <span class="audit-seq">#${event.sequence}</span>
    <span class="audit-type">${escapeHtml(event.event_type.toUpperCase())}</span>
    <span class="audit-actor">${escapeHtml(event.actor_id)}</span>
    <span class="audit-time">${escapeHtml(new Date(event.occurred_at).toLocaleString())}</span>
    <span class="audit-summary">${escapeHtml(eventSummary(event))}</span>
    <span class="audit-hash">${escapeHtml(event.event_hash.slice(0, 16))}…</span>
  </button>`;
}

function openEvent(index) {
  const event = auditEvents[index];
  if (!event) return;
  document.querySelector("#eventDetail").innerHTML = `
    <span class="source-id">EVENT #${event.sequence}</span>
    <h3>${escapeHtml(event.event_type)}</h3>
    <div class="source-meta">${escapeHtml(event.actor_id)} · ${escapeHtml(event.occurred_at)}</div>
    <pre>${escapeHtml(JSON.stringify(event, null, 2))}</pre>`;
  eventDialog.showModal();
}

async function loadAudit() {
  const [verifyResponse, eventsResponse] = await Promise.all([
    fetch("/api/audit/verify"),
    fetch("/api/audit/events?limit=50"),
  ]);
  if (!verifyResponse.ok || !eventsResponse.ok) throw new Error("Audit API unavailable");
  const verification = await verifyResponse.json();
  const eventData = await eventsResponse.json();
  auditEvents = eventData.events;
  document.querySelector("#chainStatus").textContent = verification.valid ? "VALID" : "FAILED";
  document.querySelector("#eventCount").textContent = verification.events_checked.toLocaleString();
  document.querySelector("#headHash").textContent = verification.head_hash || "GENESIS / NO EVENTS";
  document.querySelector("#chainBadge").textContent = verification.valid ? "✓ CHAIN VALID" : "! CHAIN FAILED";
  document.querySelector("#chainBadge").style.color = verification.valid ? "var(--accent)" : "var(--warm)";
  document.querySelector("#auditTable").innerHTML = auditEvents.length
    ? auditEvents.map(eventRow).join("")
    : "<div class='audit-row'><span class='audit-summary'>No events yet. Run a research question first.</span></div>";
}

document.querySelector("#auditTable").addEventListener("click", (event) => {
  const row = event.target.closest("[data-event-index]");
  if (row) openEvent(Number(row.dataset.eventIndex));
});
document.querySelector("#eventClose").addEventListener("click", () => eventDialog.close());
eventDialog.addEventListener("click", (event) => { if (event.target === eventDialog) eventDialog.close(); });
loadAudit().catch((error) => {
  document.querySelector("#chainBadge").textContent = "AUDIT OFFLINE";
  document.querySelector("#auditTable").textContent = error.message;
});
