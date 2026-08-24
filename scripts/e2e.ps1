param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Output = "artifacts/reports/e2e_smoke.json"
)

$ErrorActionPreference = "Stop"
$query = "機械学習を用いたレーザ加工技術の課題と解決手段を比較してください"

$health = Invoke-RestMethod -Uri "$BaseUrl/api/health"
if (-not $health.retrieval_ready) {
    throw "Retrieval index is not ready."
}

$payload = @{
    query = $query
    answer_language = "ja"
    top_k = 4
    actor_id = "e2e-analyst"
    session_id = "portfolio-e2e"
    require_review = $true
} | ConvertTo-Json

$search = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/search" `
    -ContentType "application/json; charset=utf-8" -Body $payload
if ($search.results.Count -lt 1) {
    throw "Search returned no evidence."
}

$answer = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/answer" `
    -ContentType "application/json; charset=utf-8" -Body $payload
if (-not $answer.grounded -or $answer.cited_source_ids.Count -lt 1) {
    throw "Answer failed the grounding contract."
}

$reviewPayload = @{
    answer_audit_id = $answer.audit_id
    reviewer_id = "e2e-reviewer"
    decision = "approved"
    notes = "Automated E2E approval after citation and source checks."
} | ConvertTo-Json
$review = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/review" `
    -ContentType "application/json; charset=utf-8" -Body $reviewPayload
$auditVerification = Invoke-RestMethod -Uri "$BaseUrl/api/audit/verify"
if (-not $auditVerification.valid) {
    throw "Audit hash-chain verification failed."
}

$record = [ordered]@{
    checked_at = (Get-Date).ToUniversalTime().ToString("o")
    base_url = $BaseUrl
    cost_mode = $health.cost_mode
    retrieval_ready = $health.retrieval_ready
    ollama_model_ready = $health.ollama.model_ready
    query = $query
    top_document_id = $search.results[0].document_id
    top_section = $search.results[0].section
    search_retrieval_ms = $search.retrieval_ms
    answer_mode = $answer.mode
    answer_model = $answer.model
    cited_source_ids = @($answer.cited_source_ids)
    answer_audit_id = $answer.audit_id
    answer_audit_hash = $answer.audit_hash
    review_status = $review.review_status
    review_audit_id = $review.review_audit_id
    review_audit_hash = $review.review_audit_hash
    audit_chain_valid = $auditVerification.valid
    audit_events_checked = $auditVerification.events_checked
    audit_head_hash = $auditVerification.head_hash
    answer_retrieval_ms = $answer.retrieval_ms
    generation_ms = $answer.generation_ms
    total_ms = $answer.total_ms
}

$outputPath = [System.IO.Path]::GetFullPath($Output)
$outputDirectory = Split-Path -Parent $outputPath
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outputPath -Encoding utf8
$record | Format-List
Write-Host "E2E evidence written to $outputPath" -ForegroundColor Green
