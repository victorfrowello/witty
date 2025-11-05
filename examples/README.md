# Example Input Files for Witty

This directory contains example natural language inputs demonstrating different logical structures and edge cases that the Witty formalization pipeline handles.

## Files

### simple_conditional.txt
A basic conditional statement (if-then) with two atomic claims.
- **Structure**: Simple implication
- **Use case**: Testing basic logical form generation and CNF transformation
- **Expected output**: Two atomic claims with implication relationship

### universal_quantifier.txt
Statement with universal quantification ("all employees") and a disjunction.
- **Structure**: Universal quantifier + disjunction
- **Use case**: Testing quantifier reduction and multi-clause logic
- **Expected output**: Quantifier reduced to propositional form with multiple claims

### causal_chain.txt
Causal reasoning with multiple connected events.
- **Structure**: Causal chain (because...and this caused...)
- **Use case**: Testing temporal/causal relationship detection
- **Expected output**: Multiple atomic claims with causal metadata

### modal_necessity.txt
Modal logic statement using "necessary" operator.
- **Structure**: Modal necessity + universal quantifier
- **Use case**: Testing modal detection and framing
- **Expected output**: Claims with modal metadata indicating necessity

### disjunctive_syllogism.txt
A complete argument with premises and conclusion.
- **Structure**: Disjunction + negation + conclusion
- **Use case**: Testing argument structure and inference detection
- **Expected output**: Multiple related claims representing the logical argument

## Using These Examples

Run any example through the CLI:

```powershell
python -m src.cli --input examples/simple_conditional.txt --output output.json --reproducible
```

Or use them in integration tests to validate pipeline behavior across different input types.
