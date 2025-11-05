import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from src.pipeline.orchestrator import formalize_statement
from src.witty.types import FormalizeOptions
import json

opts = FormalizeOptions()
text = "If Alice owns a red car then she likely prefers driving. She said she doesn't like long trips."
res = formalize_statement(text, opts)
print(json.dumps(res.model_dump(), indent=2, default=str))
