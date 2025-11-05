# Sprint 1 Documentation Index

This directory contains all documentation for the Witty formalization engine.

## Quick Links

### For New Users
- **[README.md](../README.md)** - Start here! Project overview and Sprint 1 quickstart
- **[CLI Usage Guide](CLI_Usage_Guide.md)** - Comprehensive guide to using the command-line interface

### For Development
- **[Design Specification](DesignSpec_forCopilot_v4.md)** - Authoritative technical specification
- **[Sprint 1 Plan](sprint1_plan.md)** - Development plan and task breakdown
- **[Sprint 1 Documentation Summary](Sprint1_Documentation_Summary.md)** - Completion summary and testing guide

### For Demonstrations
See the **[Sprint 1 Documentation Summary](Sprint1_Documentation_Summary.md)** for:
- Demo scripts and workflows
- Example usage scenarios
- Troubleshooting tips

## Document Overview

### README.md (Project Root)
The main project README with:
- What Witty produces
- How to call it
- Data pipeline stages
- LLM usage policy
- Project structure
- **Sprint 1 Quickstart** section with installation and basic usage

### CLI_Usage_Guide.md
Comprehensive 400+ line guide covering:
- Prerequisites and setup
- Complete CLI arguments reference
- Configuration management (.env and YAML)
- Reproducible mode explained
- Output format documentation
- Multiple usage examples
- Troubleshooting section
- Advanced programmatic API usage

### DesignSpec_forCopilot_v4.md
The authoritative technical specification:
- Purpose, scope, and non-goals
- Public API and entry points
- High-level pipeline architecture
- Data models and JSON schemas
- Module contracts and signatures
- LLM-first policies
- Provenance and privacy rules
- Orchestrator behavior
- Prompts and versioning
- CNF and modal handling
- Testing and acceptance criteria

### sprint1_plan.md
Development roadmap for Sprint 1:
- Goals and scope
- Task breakdown with time estimates
- Testing strategy
- Definition of done
- Risk register

### Sprint1_Documentation_Summary.md
Completion summary for Sprint 1 Step 5:
- Deliverables checklist
- How to use the CLI guide
- Demo scripts and workflows
- Current capabilities and limitations
- Testing and validation procedures
- Documentation structure overview

## File Organization

```
docs/
├── README.md (this file)           # Documentation index
├── CLI_Usage_Guide.md              # User guide for CLI
├── DesignSpec_forCopilot_v4.md     # Technical specification
├── DesignSpec_public.md            # Public design doc
├── DevPlan_published.md            # Development plan (published)
├── DevPlan.md                      # Internal development plan
├── sprint1_plan.md                 # Sprint 1 detailed plan
├── Sprint1_Documentation_Summary.md # Sprint 1 completion summary
└── requirements.txt                # Documentation dependencies
```

## Quick Start Paths

### "I want to use Witty"
1. Read [../README.md](../README.md) - Sprint 1 Quickstart section
2. Read [CLI_Usage_Guide.md](CLI_Usage_Guide.md) - Examples section
3. Run `demo.bat` in the project root

### "I want to develop Witty"
1. Read [DesignSpec_forCopilot_v4.md](DesignSpec_forCopilot_v4.md) - Complete specification
2. Read [sprint1_plan.md](sprint1_plan.md) - Current sprint plan
3. Review [Sprint1_Documentation_Summary.md](Sprint1_Documentation_Summary.md) - Current state

### "I want to demo Witty to someone"
1. Read [Sprint1_Documentation_Summary.md](Sprint1_Documentation_Summary.md) - Demo section
2. Run `demo.bat` in project root
3. Show example outputs from `tests/fixtures/`

## Additional Resources

### Examples
See `../examples/` directory for:
- Sample input text files
- README explaining each example
- Different logical structures demonstrated

### Test Fixtures
See `../tests/fixtures/` directory for:
- Example JSON outputs for each pipeline stage
- Schema validation examples
- README explaining fixture usage

### Demo Scripts
In the project root:
- `demo.bat` - Batch file demo (no execution policy needed)
- `demo.ps1` - PowerShell demo (requires execution policy change)

## Maintenance

### Updating Documentation
When adding new features:
1. Update the relevant specification in `DesignSpec_forCopilot_v4.md`
2. Add usage examples to `CLI_Usage_Guide.md`
3. Update `README.md` if public-facing changes
4. Add fixtures to `tests/fixtures/` if new schemas introduced

### Version History
- **v1.0** (Sprint 1) - November 4, 2025
  - Initial documentation complete
  - CLI usage guide created
  - Example files and fixtures added
  - Demo scripts provided

---

*Last updated: November 4, 2025*
