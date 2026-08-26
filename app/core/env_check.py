"""Environment validation utilities."""

import os
from pathlib import Path


def ensure_env_file() -> None:
    """
    Ensure .env file exists. If not, copy from .env.example and exit with instructions.
    """
    env_path = Path(".env")
    example_path = Path(".env.example")

    if not env_path.exists():
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
        print("❌ .env file not found. Created from .env.example.")
        print("   Please edit .env and add your GEMINI_API_KEY before running.")
        exit(1)

    # Check if GEMINI_API_KEY is set to a real value
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("❌ GEMINI_API_KEY not set in .env")
        print("   Please edit .env and add your Google AI Studio API key.")
        print("   Get one at: https://aistudio.google.com/app/apikey")
        exit(1)