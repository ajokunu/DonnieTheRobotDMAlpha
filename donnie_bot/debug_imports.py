"""
Debug script to find exactly where imports fail
"""
import sys
from pathlib import Path

# Add src to path (same as main.py)
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("🔍 Testing import chain step by step...")

try:
    print("1. Testing aiosqlite directly...")
    import aiosqlite
    print("   ✅ aiosqlite works")
except Exception as e:
    print(f"   ❌ aiosqlite failed: {e}")
    exit(1)

try:
    print("2. Testing domain entities...")
    from src.domain.entities import Character
    print("   ✅ domain entities work")
except Exception as e:
    print(f"   ❌ domain entities failed: {e}")
    exit(1)

try:
    print("3. Testing infrastructure config...")
    from src.infrastructure.config.settings import settings
    print("   ✅ infrastructure config works")
except Exception as e:
    print(f"   ❌ infrastructure config failed: {e}")
    exit(1)

try:
    print("4. Testing infrastructure.database.__init__...")
    from src.infrastructure.database import SQLiteRepositoryFactory
    print("   ✅ database __init__ works")
except Exception as e:
    print(f"   ❌ database __init__ failed: {e}")
    print(f"   Error details: {type(e).__name__}: {e}")
    exit(1)

try:
    print("5. Testing sqlite_repository directly...")
    from src.infrastructure.database.sqlite_repository import SQLiteRepositoryFactory
    print("   ✅ sqlite_repository works")
except Exception as e:
    print(f"   ❌ sqlite_repository failed: {e}")
    print(f"   Error details: {type(e).__name__}: {e}")
    exit(1)

try:
    print("6. Testing infrastructure.__init__...")
    from src.infrastructure import settings
    print("   ✅ infrastructure __init__ works")
except Exception as e:
    print(f"   ❌ infrastructure __init__ failed: {e}")
    print(f"   Error details: {type(e).__name__}: {e}")
    exit(1)

try:
    print("7. Testing logging import...")
    from src.infrastructure.config.logging import setup_logging
    print("   ✅ logging import works")
except Exception as e:
    print(f"   ❌ logging import failed: {e}")
    print(f"   Error details: {type(e).__name__}: {e}")
    exit(1)

print("🎉 All imports successful!")