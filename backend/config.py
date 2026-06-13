"""Flask application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


class Config:
    """Default configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    DATA_DIR = DATA_DIR
