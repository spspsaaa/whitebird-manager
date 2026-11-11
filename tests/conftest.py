import os

os.environ.setdefault("BOT_TOKEN", "123456789:AAtesttokenforunittestsonly")
os.environ.setdefault("OWNER_ID", "42")

# A valid Fernet key for the tests only - never used outside the test suite.
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./data/test.db")
os.environ.setdefault("TOKEN_STORE_DIR", "./data/test-tokens")
