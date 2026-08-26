"""Environment validation utilities."""

import os
import sys
from pathlib import Path
import httpx


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
        print("[ERROR] .env file not found. Created from .env.example.")
        print("   Please edit .env and add your OLLAMA_HOST and OLLAMA_MODEL before running.")
        sys.exit(1)


def check_ollama_health() -> bool:
    """
    Check if Ollama is running and the model is available.
    Returns True if healthy, False otherwise.
    """
    from app.core.config import settings
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.OLLAMA_HOST}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(settings.OLLAMA_MODEL in m for m in model_names):
                    print(f"[OK] Ollama is running at {settings.OLLAMA_HOST}")
                    print(f"[OK] Model '{settings.OLLAMA_MODEL}' is available")
                    return True
                else:
                    print(f"[WARN] Ollama is running but model '{settings.OLLAMA_MODEL}' not found.")
                    print(f"   Available models: {model_names}")
                    print(f"   Run: ollama pull {settings.OLLAMA_MODEL}")
                    return False
            else:
                print(f"[ERROR] Ollama returned status {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"[ERROR] Cannot connect to Ollama at {settings.OLLAMA_HOST}")
        print("   Ensure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"[ERROR] Ollama health check failed: {e}")
        return False