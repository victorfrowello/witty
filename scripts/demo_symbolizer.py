"""Demo script showing symbolizer in action."""
from src.pipeline.symbolizer import symbolizer
from src.witty_types import AtomicClaim, ConcisionResult, FormalizeOptions
from src.pipeline.orchestrator import AgentContext
import json

# Create context
ctx = AgentContext('demo', FormalizeOptions(), deterministic_salt='demo')

# Create test claims with a duplicate
claims = [
    AtomicClaim(text='it rains', origin_spans=[(3, 11)]),
    AtomicClaim(text='match is cancelled', origin_spans=[(16, 34)]),
    AtomicClaim(text='it rains', origin_spans=[(50, 58)])  # Duplicate
]

# Create concision result
conc = ConcisionResult(
    canonical_text='if it rains then match is cancelled and it rains again',
    atomic_candidates=claims
)

# Run symbolizer
result = symbolizer(conc, ctx)

# Display results
print('=== SYMBOLIZATION DEMO ===\n')
print('Legend:')
print(json.dumps(result.payload['legend'], indent=2))

print('\nSymbols Assigned:')
for claim in result.payload['atomic_claims']:
    print(f'  {claim["symbol"]}: {claim["text"]} (origin: {claim["origin_spans"]})')

print('\nDuplicate Handling:')
print(f'  3 claims input, {len(result.payload["legend"])} unique symbols assigned')
sym0 = result.payload["atomic_claims"][0]["symbol"]
sym2 = result.payload["atomic_claims"][2]["symbol"]
print(f'  Duplicate "it rains" uses same symbol: {sym0} == {sym2}')

print('\nProvenance:')
print(f'  Module: {result.provenance_record.module_id} v{result.provenance_record.module_version}')
print(f'  Provenance ID: {result.provenance_record.id}')
print(f'  Confidence: {result.confidence}')
print(f'  Events: {len(result.provenance_record.event_log)} logged')
print('\n✅ Symbolization Complete!')
