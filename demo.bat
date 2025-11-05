@echo off
REM Quick Demo Script for Witty CLI (Windows Batch Version)
REM Run this to demonstrate the system to others

echo.
echo ================================================
echo    Witty Formalization Engine - Demo
echo    Sprint 1: Deterministic Mock Pipeline
echo ================================================
echo.

REM Demo 1: Simple Conditional
echo --- Example 1: Simple Conditional ---
echo.
echo Input:
type examples\simple_conditional.txt
echo.
echo Processing...
echo.

python -m src.cli --input examples\simple_conditional.txt --output demo_simple.json --reproducible --verbosity normal

echo.
echo Results saved to demo_simple.json
echo.

REM Demo 2: Modal Statement
echo --- Example 2: Modal Logic ---
echo.
echo Input:
type examples\modal_necessity.txt
echo.
echo Processing...
echo.

python -m src.cli --input examples\modal_necessity.txt --output demo_modal.json --reproducible --verbosity normal

echo.
echo Results saved to demo_modal.json
echo.

REM Demo 3: Complex Argument
echo --- Example 3: Logical Argument ---
echo.
echo Input:
type examples\disjunctive_syllogism.txt
echo.
echo Processing...
echo.

python -m src.cli --input examples\disjunctive_syllogism.txt --output demo_argument.json --reproducible --verbosity normal

echo.
echo Results saved to demo_argument.json
echo.

REM Summary
echo.
echo ================================================
echo              Demo Complete!
echo ================================================
echo.
echo Output files created:
echo   - demo_simple.json
echo   - demo_modal.json
echo   - demo_argument.json
echo.
echo To view full output (PowerShell):
echo   cat demo_simple.json ^| ConvertFrom-Json ^| ConvertTo-Json -Depth 10
echo.
echo To clean up demo files:
echo   del demo_*.json
echo.
