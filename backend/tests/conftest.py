import pytest
from app.engine.memory import user_rule_memory


@pytest.fixture(autouse=True)
def clean_memory_state():
    user_rule_memory.clear()
    yield
    user_rule_memory.clear()
