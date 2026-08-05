import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Model config - HARDCODED in source code as required by section 9 of README
# Model must be <= 10B parameters
MODEL_NAME = "gemma-3-12b-it"  # Replace with your local/provider model <= 10B
MODEL_PROVIDER = "openrouter"

# API credentials loaded from environment variables (.env)
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "http://localhost:11434/v1")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")


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
