import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
DEFAULT_API_KEY = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
