import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DATA_DIR = BASE_DIR / "schema_data"

# API Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_TITLE = "AI Database Query Bot"
API_DESCRIPTION = "Text-to-SQL AI service for database querying via natural language"
API_VERSION = "0.1.0"

# PostgreSQL Database Settings
DB_URL = os.getenv("DB_URL")

# MongoDB Settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "aibot")
MONGODB_CONVERSATION_COLLECTION = os.getenv("MONGODB_CONVERSATION_COLLECTION", "conversations")

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

# Schema Settings
SCHEMA_MAX_TABLES = int(os.getenv("SCHEMA_MAX_TABLES", "20"))
SCHEMA_MAX_VIEWS = int(os.getenv("SCHEMA_MAX_VIEWS", "10")) 