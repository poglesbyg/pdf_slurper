#!/usr/bin/env python3
"""Test database connection to see what's happening."""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.config.settings import Settings

# Get settings
settings = Settings()
print(f"Database URL: {settings.database_url}")
print(f"Data dir: {settings.data_dir}")

# Try to connect
from sqlmodel import create_engine, Session, select
engine = create_engine(settings.database_url, echo=False)

try:
    with Session(engine) as session:
        result = session.exec(select(1))
        print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database error: {e}")

# Check what path it resolves to
if "sqlite" in settings.database_url:
    db_path = settings.database_url.replace("sqlite:///", "")
    print(f"SQLite path: {db_path}")
    print(f"Path exists: {Path(db_path).exists()}")
    print(f"Path absolute: {Path(db_path).absolute()}")
