"""
Quick verification script for the concision module.
Demonstrates various capabilities with example inputs.
"""
from src.pipeline.preprocessing import preprocess
from src.pipeline.concision import deterministic_concision
from src.pipeline.orchestrator import AgentContext
from src.witty_types import FormalizeOptions


def demo_concision(text: str, description: str):
    """Run concision on a text and display results."""
    print(f"\n{'='*70}")
    print(f"DEMO: {description}")
    print(f"{'='*70}")
    print(f"Input: {text}\n")
    
    # Preprocessing
    prep_result = preprocess(text)
    
    # Concision
    ctx = AgentContext(
        request_id=f"demo_{description.lower().replace(' ', '_')}",
        options=FormalizeOptions(),
        reproducible_mode=True,
        deterministic_salt="demo"
    )
    conc_result = deterministic_concision(prep_result, ctx)
    
    # Display results
    print(f"Results:")
    print(f"  Atomic Candidates: {len(conc_result.payload['atomic_candidates'])}")
    for i, candidate in enumerate(conc_result.payload['atomic_candidates'], 1):
        print(f"    {i}. \"{candidate['text']}\"")
        print(f"       Origin: {candidate['origin_spans']}")
    print(f"  Confidence: {conc_result.confidence}")
    print(f"  Provenance ID: {conc_result.provenance_record.id}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("WITTY CONCISION MODULE - DEMONSTRATION")
    print("="*70)
    
    # Test 1: Simple conditional
    demo_concision(
        "If it rains, then the match is cancelled.",
        "Simple Conditional (If-Then)"
    )
    
    # Test 2: Conjunction
    demo_concision(
        "The server crashed and the website went offline.",
        "Conjunction (AND)"
    )
    
    # Test 3: Biconditional
    demo_concision(
        "The light is on if and only if the switch is up.",
        "Biconditional (IFF)"
    )
    
    # Test 4: Simple declarative
    demo_concision(
        "The cat sat on the mat.",
        "Simple Declarative"
    )
    
    # Test 5: Negation preservation
    demo_concision(
        "If it's not raining, then the picnic will proceed.",
        "Negation Preservation"
    )
    
    # Test 6: Quantifier preservation
    demo_concision(
        "If all students attend, then class will start on time.",
        "Quantifier Preservation"
    )
    
    # Test 7: When pattern
    demo_concision(
        "When the alarm sounds, evacuate the building immediately.",
        "When-Pattern Conditional"
    )
    
    # Test 8: Multiple sentences
    demo_concision(
        "The dog barked. The cat ran away.",
        "Multiple Simple Sentences"
    )
    
    print(f"\n{'='*70}")
    print("DEMONSTRATION COMPLETE")
    print(f"{'='*70}\n")
