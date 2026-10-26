from typing import Protocol
from app.brain.models import Transaction

class StatementParser(Protocol):
    def parse(self, file_bytes: bytes) -> list[Transaction]: ...