# app/models/whmcs.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from app.database.session import Base


class WhmcsImportBatch(Base):
    __tablename__ = "whmcs_import_batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="draft")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class WhmcsImportRow(Base):
    __tablename__ = "whmcs_import_rows"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("whmcs_import_batches.id"), nullable=False, index=True)
    row_type = Column(String, nullable=False)
    source_id = Column(String, nullable=True)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")
    message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
