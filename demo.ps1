# Quick Demo Script for Witty CLI
# Run this to demonstrate the system to others
#
# NOTE: If you get an execution policy error, run this first:
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Or use the demo.bat file instead (no execution policy needed)

Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Witty Formalization Engine - Demo       ║" -ForegroundColor Cyan
Write-Host "║   Sprint 1: Deterministic Mock Pipeline   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Demo 1: Simple Conditional
Write-Host "━━━ Example 1: Simple Conditional ━━━" -ForegroundColor Yellow
Write-Host ""
Write-Host "Input:" -ForegroundColor Green
Get-Content examples/simple_conditional.txt
Write-Host ""
Write-Host "Processing..." -ForegroundColor Gray

python -m src.cli `
  --input examples/simple_conditional.txt `
  --output demo_simple.json `
  --reproducible `
  --verbosity normal

if ($LASTEXITCODE -eq 0) {
    $result = Get-Content demo_simple.json | ConvertFrom-Json
    
    Write-Host ""
    Write-Host "Results:" -ForegroundColor Green
    Write-Host "  Canonical: $($result.canonical_text)" -ForegroundColor White
    Write-Host "  Atomic claims:" -ForegroundColor White
    foreach ($claim in $result.atomic_claims) {
        Write-Host "    • $($claim.symbol): $($claim.text)" -ForegroundColor Cyan
    }
    Write-Host "  CNF: $($result.cnf)" -ForegroundColor White
    Write-Host "  Confidence: $($result.confidence)" -ForegroundColor White
    Write-Host ""
}

# Demo 2: Modal Statement
Write-Host "━━━ Example 2: Modal Logic ━━━" -ForegroundColor Yellow
Write-Host ""
Write-Host "Input:" -ForegroundColor Green
Get-Content examples/modal_necessity.txt
Write-Host ""
Write-Host "Processing..." -ForegroundColor Gray

python -m src.cli `
  --input examples/modal_necessity.txt `
  --output demo_modal.json `
  --reproducible `
  --verbosity normal

if ($LASTEXITCODE -eq 0) {
    $result = Get-Content demo_modal.json | ConvertFrom-Json
    
    Write-Host ""
    Write-Host "Results:" -ForegroundColor Green
    Write-Host "  Canonical: $($result.canonical_text)" -ForegroundColor White
    Write-Host "  Atomic claims: $($result.atomic_claims.Count)" -ForegroundColor White
    Write-Host "  CNF: $($result.cnf)" -ForegroundColor White
    Write-Host "  Confidence: $($result.confidence)" -ForegroundColor White
    Write-Host ""
}

# Demo 3: Complex Argument
Write-Host "━━━ Example 3: Logical Argument ━━━" -ForegroundColor Yellow
Write-Host ""
Write-Host "Input:" -ForegroundColor Green
Get-Content examples/disjunctive_syllogism.txt
Write-Host ""
Write-Host "Processing..." -ForegroundColor Gray

python -m src.cli `
  --input examples/disjunctive_syllogism.txt `
  --output demo_argument.json `
  --reproducible `
  --verbosity normal

if ($LASTEXITCODE -eq 0) {
    $result = Get-Content demo_argument.json | ConvertFrom-Json
    
    Write-Host ""
    Write-Host "Results:" -ForegroundColor Green
    Write-Host "  Canonical: $($result.canonical_text)" -ForegroundColor White
    Write-Host "  Atomic claims extracted: $($result.atomic_claims.Count)" -ForegroundColor White
    Write-Host "  Legend:" -ForegroundColor White
    foreach ($key in $result.legend.PSObject.Properties.Name) {
        Write-Host "    $key -> $($result.legend.$key)" -ForegroundColor Cyan
    }
    Write-Host "  CNF: $($result.cnf)" -ForegroundColor White
    Write-Host ""
}

# Summary
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            Demo Complete!                  ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Output files created:" -ForegroundColor Yellow
Write-Host "  • demo_simple.json" -ForegroundColor White
Write-Host "  • demo_modal.json" -ForegroundColor White
Write-Host "  • demo_argument.json" -ForegroundColor White
Write-Host ""
Write-Host "To view full output:" -ForegroundColor Yellow
Write-Host "  cat demo_simple.json | ConvertFrom-Json | ConvertTo-Json -Depth 10" -ForegroundColor Cyan
Write-Host ""
Write-Host "To clean up demo files:" -ForegroundColor Yellow
Write-Host "  Remove-Item demo_*.json" -ForegroundColor Cyan
Write-Host ""
