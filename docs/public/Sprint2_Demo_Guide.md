# Witty Sprint 2 Demonstration Guide

**For**: Non-Technical Audiences  
**Date**: November 5, 2025  
**Version**: v0.1.5 (Sprint 2 Complete)

---

## What is Witty?

Witty is like a **translator** that converts everyday English statements into precise logical formulas that computers can understand and reason about. Think of it as breaking down a complex sentence into its simplest building blocks, then organizing those blocks in a way that a machine can work with.

### Analogy

Imagine you have a LEGO model of a house. Witty is like:
1. Taking the house apart into individual bricks
2. Labeling each brick (P1, P2, P3, etc.)
3. Writing down instructions for how they fit together
4. Keeping a record of where each brick came from in the original house

This way, anyone (or any computer) can:
- See exactly what bricks you have
- Understand how they connect
- Rebuild the same house
- Check if the instructions make sense

---

## What You'll See in This Demo

We'll show you **6 demonstrations** that highlight different capabilities:

1. **Simple Conditional**: "If it rains, then the match is cancelled"
   - Shows basic breakdown into atomic parts

2. **Quantified Statement**: "All employees must submit timesheets"
   - Shows how Witty handles "all", "some", "every"

3. **Nested Structure**: "If Alice studies hard and passes the exam, then she graduates"
   - Shows handling of complex, nested logic

4. **Complex Real-World**: Multiple connected statements
   - Shows how Witty handles longer, realistic text

5. **Reproducibility**: Running the same input multiple times
   - Proves results are consistent and reliable

6. **Complete Output**: Full JSON result
   - Shows what the system actually produces

---

## Running the Demo

### Prerequisites

You need:
- Python 3.10 or higher installed
- The Witty project downloaded
- A terminal/command prompt

### Step-by-Step Instructions

#### On Windows (PowerShell):

```powershell
# 1. Navigate to the Witty directory
cd C:\path\to\witty-1

# 2. Activate the virtual environment (if you have one)
.\venv\Scripts\Activate.ps1

# 3. Run the demo script as a module
python -m scripts.demo_sprint2
```

#### On Mac/Linux (Terminal):

```bash
# 1. Navigate to the Witty directory
cd /path/to/witty-1

# 2. Activate the virtual environment (if you have one)
source venv/bin/activate

# 3. Run the demo script as a module
python -m scripts.demo_sprint2
```

### What to Expect

The demo is **interactive**. It will:
1. Show you an example statement
2. Break it down step by step
3. Explain what Witty did
4. Wait for you to press Enter before moving to the next demo

**Total time**: About 5-10 minutes if you read everything carefully.

---

## Understanding the Output

### Key Concepts Explained Simply

#### 1. **Atomic Claims**

These are the simplest possible statements that can't be broken down further.

**Example**:
- Input: "If it rains, then the match is cancelled"
- Atomic Claims:
  - Claim 1: "it rains"
  - Claim 2: "the match is cancelled"

Think of them as LEGO bricks - you can't break a single brick into smaller pieces.

#### 2. **Symbols**

These are short labels (P1, P2, P3, etc.) that Witty assigns to each atomic claim.

**Why?** It's easier for computers to work with "P1" than "it rains".

**Example**:
- P1 = "it rains"
- P2 = "the match is cancelled"

#### 3. **Legend**

A dictionary that translates symbols back to English.

```
Legend:
  P1 = "it rains"
  P2 = "the match is cancelled"
```

#### 4. **CNF (Conjunctive Normal Form)**

This is the formal logical representation using symbols.

**Example**:
- Input: "If it rains, then the match is cancelled"
- CNF: `¬P1 ∨ P2`
- Meaning: "NOT (it rains) OR (the match is cancelled)"

This is mathematically equivalent to the original if-then statement.

#### 5. **Origin Spans**

These are the character positions in the original text where each claim came from.

**Example**:
```
Original text: "If it rains, then the match is cancelled."
                   ^^^^^^^
                   3 to 11

Claim: "it rains"
Origin span: [3, 11]
```

This proves Witty didn't make anything up - every claim comes from the original text.

#### 6. **Provenance**

A detailed record of every step Witty took to process the input.

Think of it like a **receipt** or **audit trail**:
- What module processed the text?
- What version of the module?
- How confident was it?
- What decisions did it make?

This ensures transparency and accountability.

#### 7. **Confidence**

A score from 0.0 to 1.0 (0% to 100%) showing how confident Witty is in its results.

- **0.95** (95%): Very confident
- **0.70** (70%): Moderately confident
- **0.50** (50%): Low confidence, might need human review

---

## Demonstrating to Others

### For Business Stakeholders

**Focus on**: Value and reliability
- Emphasize **reproducibility** (Demo 5)
- Highlight **provenance** for auditability
- Show **real-world example** (Demo 4)

**Key messages**:
- "Same input always gives same output - perfect for compliance"
- "Every decision is documented for audit trails"
- "Can process complex business rules consistently"

### For Technical Audiences

**Focus on**: Architecture and testing
- Show **complete output** (Demo 6)
- Explain **modular pipeline** design
- Highlight **test coverage** (246 tests)

**Key messages**:
- "Fully deterministic for CI/CD integration"
- "Extensive test coverage with edge cases"
- "Schema-validated outputs"

### For Non-Technical Users

**Focus on**: Simplicity and understanding
- Use **simple conditional** (Demo 1)
- Show **origin tracing** (Demo 3)
- Keep explanations high-level

**Key messages**:
- "Like a translator from English to computer language"
- "Every part can be traced back to the original"
- "Works consistently every time"

---

## Common Questions & Answers

### Q: Does it use AI or machine learning?

**A**: Sprint 2 is **deterministic** - it uses rules and algorithms, not AI. Sprint 4 will add optional LLM (AI) assistance, but there will always be a deterministic fallback.

### Q: Is it accurate?

**A**: For the logical structures it's designed to handle (conditionals, quantifiers, conjunctions), it's very accurate. We have 246 tests verifying correctness. However, natural language is complex - some edge cases may require human review.

### Q: Can it handle any English sentence?

**A**: Not yet. Sprint 2 handles:
- Conditionals (if-then, when, unless, etc.)
- Quantifiers (all, some, every, etc.)
- Conjunctions (and, or, but)
- Simple declarative statements

Complex nested structures and ambiguous statements may be partially processed.

### Q: How fast is it?

**A**: Very fast for short inputs (< 1 second). Longer documents (> 1000 words) may take a few seconds. Performance hasn't been optimized yet.

### Q: Can I trust the results?

**A**: Yes, because of:
1. **Provenance**: Every step is documented
2. **Origin spans**: Every claim is traceable to source text
3. **Tests**: 246 automated tests verify correctness
4. **Reproducibility**: Same input always gives same output

If you see a low confidence score, that's a signal to review manually.

### Q: What can I do with the output?

**A**: The JSON output can be:
- Stored in databases
- Passed to theorem provers
- Used to build knowledge graphs
- Integrated into fact-checking systems
- Analyzed for consistency
- Compared with other formalizations

### Q: Is this the final version?

**A**: No, this is Sprint 2 (of 6 planned sprints). Upcoming features:
- Sprint 3: Full CNF transformation, validation
- Sprint 4: LLM integration for complex cases
- Sprint 5: Modal logic, temporal reasoning
- Sprint 6: Multi-document reasoning

---

## What to Check Manually Before Public Demo

### 1. Environment Setup

- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Python version 3.10+ (`python --version`)
- [ ] spaCy model downloaded (`python -m spacy download en_core_web_sm`)

### 2. Run the Demo Script Once

```powershell
python scripts/demo_sprint2.py
```

- [ ] All 6 demos run without errors
- [ ] Output looks reasonable
- [ ] No exceptions or warnings

### 3. Check Test Suite

```powershell
python -m pytest tests/ -q
```

- [ ] Expected result: `246 passed, 1 skipped`
- [ ] No failures

### 4. Test Example Files

```powershell
# Test a few examples manually
python -m src.cli --input examples/simple_conditional.txt --output test_output.json --reproducible
```

- [ ] Command runs without errors
- [ ] Output file created
- [ ] JSON is valid (open in text editor)

### 5. Verify Key Features

Run this quick verification script:

```python
from src.pipeline.orchestrator import formalize_statement
from src.witty_types import FormalizeOptions

text = "If it rains, the match is cancelled."
opts = FormalizeOptions(reproducible_mode=True)
result = formalize_statement(text, opts)

# Quick checks
assert len(result.atomic_claims) == 2
assert result.confidence > 0.9
assert len(result.provenance) >= 2
print("✅ All quick checks passed!")
```

- [ ] Quick checks pass
- [ ] Confidence is high
- [ ] Provenance exists

### 6. Prepare Backup

In case something goes wrong during the live demo:

- [ ] Have pre-generated output JSON files ready
- [ ] Screenshot of successful test run
- [ ] This guide printed or easily accessible

---

## Troubleshooting

### "Module not found" error

```powershell
# Make sure you're in the right directory
cd C:\path\to\witty-1

# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### "spaCy model not found" error

```powershell
# Download the spaCy English model
python -m spacy download en_core_web_sm
```

### Demo script crashes

```powershell
# Run with verbose error output
python -u scripts/demo_sprint2.py
```

Check the error message and:
1. Verify all dependencies are installed
2. Make sure you're using Python 3.10+
3. Try running the test suite to see if there are deeper issues

### JSON output looks wrong

This usually means:
- Dependencies are out of date: `pip install -r requirements.txt --upgrade`
- Python version is too old: Upgrade to 3.10+

---

## Contact & Support

If you encounter issues:

1. **Check the logs**: Look for error messages
2. **Run the test suite**: `pytest tests/ -v`
3. **Review the implementation summary**: `docs/internal/sprints/Sprint2_Implementation_Summary.md`
4. **Contact the development team**: Include error messages and steps to reproduce

---

## Conclusion

This demo shows Sprint 2 is **production-ready**:
- ✅ Fully functional deterministic pipeline
- ✅ Comprehensive test coverage
- ✅ Schema-compliant outputs
- ✅ Complete provenance tracking
- ✅ Reproducible results

Perfect for showcasing to:
- **Business stakeholders**: Reliability and auditability
- **Technical teams**: Architecture and testing
- **End users**: Simplicity and transparency

**Estimated demo time**: 5-10 minutes  
**Difficulty level**: Easy (mostly automated, just press Enter)  
**Wow factor**: High (especially reproducibility demo)

Good luck with your demonstration!
