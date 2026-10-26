from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ImportDraft(Base):
    __tablename__ = "import_drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String, nullable=False)
    file_data: Mapped[str] = mapped_column(Text, nullable=False)  # base64-encoded bytes
    detected_mapping: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    preview_rows: Mapped[str] = mapped_column(Text, default="[]")      # JSON
    warnings: Mapped[str] = mapped_column(Text, default="[]")          # JSON
    fmt: Mapped[str] = mapped_column(String, default="csv")
    encoding: Mapped[str] = mapped_column(String, default="utf-8")
    delimiter: Mapped[str] = mapped_column(String, default=",")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
