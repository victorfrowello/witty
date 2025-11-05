"""
CLI entrypoint for Witty formalization pipeline.

Provides command-line interface for formalizing natural language statements
into logical representations. Handles argument parsing, configuration loading,
and pipeline orchestration.

Usage:
    python -m src.cli --input INPUT --output OUTPUT [OPTIONS]
"""
import os
import sys
import argparse
import logging
from typing import Any, Optional, Dict

# Ensure parent directory is in path for module imports
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import pipeline orchestrator and typed models
from src.pipeline.orchestrator import formalize_statement
from src.witty.types import FormalizeOptions, FormalizationResult

# Optional dependencies - loaded dynamically to avoid hard requirements
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def load_config(dotenv_path: Optional[str], yaml_path: Optional[str]) -> Dict[str, Any]:
    """
    Load configuration from .env and YAML files.
    
    Configuration is merged with YAML taking precedence over .env variables.
    Missing files are silently ignored.
    
    Args:
        dotenv_path: Path to .env file for environment variables
        yaml_path: Path to YAML configuration file
        
    Returns:
        Dictionary of configuration key-value pairs
    """
    config: Dict[str, Any] = {}
    
    # Load environment variables from .env file if available
    if load_dotenv is not None and dotenv_path and os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        config.update(os.environ)
    
    # Load YAML configuration if available (takes precedence)
    if yaml is not None and yaml_path and os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                config.update(loaded)
    
    return config


def setup_logging(verbosity: str) -> None:
    """
    Configure logging based on verbosity level.
    
    Sets up console logging with appropriate formatting and log level.
    
    Args:
        verbosity: Logging verbosity level ('normal' or 'debug')
    """
    level = logging.DEBUG if verbosity == 'debug' else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def main() -> None:
    """
    Main CLI entrypoint for the Witty formalization pipeline.
    
    Parses command-line arguments, loads configuration, executes the
    formalization pipeline, and writes results to the output file.
    
    Exits with status code 1 on pipeline failure.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Witty Formalization CLI - Convert natural language to formal logic"
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input file containing natural language text'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output file for FormalizationResult JSON'
    )
    parser.add_argument(
        '--config',
        help='Optional YAML configuration file'
    )
    parser.add_argument(
        '--env',
        default='.env',
        help='Path to .env file (default: .env)'
    )
    parser.add_argument(
        '--verbosity',
        choices=['normal', 'debug'],
        default='normal',
        help='Logging verbosity level'
    )
    parser.add_argument(
        '--reproducible',
        action='store_true',
        help='Enable reproducible mode with deterministic pipeline behavior'
    )
    args = parser.parse_args()

    # Configure logging based on verbosity
    setup_logging(args.verbosity)
    logging.info("Witty CLI started")
    logging.debug(f"Verbosity level: {args.verbosity}")
    
    # Log verbosity flag for test verification
    logging.info(f"Verbosity flag: {args.verbosity}")

    # Load configuration from .env and YAML files
    config = load_config(args.env, args.config)
    if args.reproducible:
        config['REPRODUCIBLE_MODE'] = 'true'
    logging.debug(f"Configuration loaded: {list(config.keys())}")

    # Build FormalizeOptions from configuration
    # Convert all keys to lowercase for case-insensitive matching
    options_dict = {k.lower(): v for k, v in config.items()}
    options = FormalizeOptions(**options_dict)
    options.reproducible_mode = args.reproducible
    options.verbosity = args.verbosity

    # Read input text from file
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_text = f.read()
        logging.info(f"Input file read: {args.input} ({len(input_text)} characters)")
    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Failed to read input file: {e}")
        sys.exit(1)

    # Execute formalization pipeline
    try:
        logging.info("Starting formalization pipeline")
        result: FormalizationResult = formalize_statement(input_text, options)
        logging.info("Formalization completed successfully")
    except Exception as e:
        logging.error(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)

    # Write FormalizationResult to output file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            # Use Pydantic's model_dump_json for proper serialization
            f.write(result.model_dump_json(indent=2, ensure_ascii=False))
        logging.info(f"FormalizationResult written to: {args.output}")
    except Exception as e:
        logging.error(f"Failed to write output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
