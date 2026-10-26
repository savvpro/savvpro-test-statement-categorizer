"""Tests for the override store (brain/overrides.py)."""

from app.brain.overrides import OverrideStore


class TestOverrideStore:
    def test_get_set(self):
        store = OverrideStore()
        assert store.get("STARBUCKS") is None
        store.set("STARBUCKS", "Meals")
        assert store.get("STARBUCKS") == "Meals"

    def test_remove(self):
        store = OverrideStore()
        store.set("STARBUCKS", "Meals")
        store.remove("STARBUCKS")
        assert store.get("STARBUCKS") is None

    def test_clear(self):
        store = OverrideStore()
        store.set("STARBUCKS", "Meals")
        store.set("UBER", "Travel")
        store.clear()
        assert store.get("STARBUCKS") is None
        assert store.get("UBER") is None

    def test_all_returns_copy(self):
        store = OverrideStore()
        store.set("STARBUCKS", "Meals")
        all_overs = store.all()
        all_overs["STARBUCKS"] = "Travel"
        assert store.get("STARBUCKS") == "Meals"
