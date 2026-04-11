"""Configuration for LLM Knesset."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Legacy compatibility — use settings_store getters at call time for live values
def get_openrouter_api_key():
    from . import settings_store
    return settings_store.get_api_key()

def get_council_models():
    from . import settings_store
    return settings_store.get_council_models()

def get_chairman_model():
    from . import settings_store
    return settings_store.get_chairman_model()

# Static fallbacks for backwards compat
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
COUNCIL_MODELS = [
    "openai/gpt-4o",
    "google/gemini-pro",
    "anthropic/claude-3-5-sonnet",
    "x-ai/grok-2",
]
CHAIRMAN_MODEL = "google/gemini-pro"
