"""Pytest configuration – override DB to in-memory SQLite for tests."""
from __future__ import annotations

import os

# Shared-cache in-memory SQLite: all connections share the same DB,
# so tables created during lifespan startup are visible to all sessions.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
