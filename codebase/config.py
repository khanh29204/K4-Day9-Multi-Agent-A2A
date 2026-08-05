import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Model config - HARDCODED in source code as required by section 9 of README
MODEL_NAME = "qwen2.5-coder:1.5b"  # e.g. qwen3:4b, qwen2.5-coder:1.5b, llama-3.1-8b-instant
MODEL_PROVIDER = "ollama"  # ollama / groq / openrouter


def extract_parameter_size(name: str) -> str:
    """Tự động trích xuất dung lượng tham số model (ví dụ: 'qwen2.5-coder:1.5b' -> '1.5B')."""
    match = re.search(r'(\d+(?:\.\d+)?)\s*b\b', name, re.IGNORECASE)
    if match:
        val = float(match.group(1))
        return f"{int(val)}B" if val.is_integer() else f"{val}B"
    return "8B"


PARAMETER_SIZE = extract_parameter_size(MODEL_NAME)

# API credentials loaded from environment variables (.env) or local Ollama default
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:11434/v1")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "ollama")


# Directory configs
CODEBASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CODEBASE_DIR, ".."))

DATA_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "data"))
INPUT_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "input"))
OUTPUT_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "output"))
LOGGING_DIR = os.path.abspath(os.path.join(PROJECT_DIR, "logging"))

TRACE_FILE = os.path.abspath(os.path.join(PROJECT_DIR, "trace.jsonl"))
METADATA_FILE = os.path.abspath(os.path.join(PROJECT_DIR, "metadata.json"))

# Execution config
MAX_RETRIES = 3
TEMPERATURE = 0.1
