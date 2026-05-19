from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class WhmcsImportRowCreate(BaseModel):
    row_type: str
    source_id: Optional[str] = None
    payload: Dict[str, Any]


class WhmcsImportBatchCreate(BaseModel):
    name: str
    rows: List[WhmcsImportRowCreate] = []


class WhmcsImportRowOut(BaseModel):
    id: int
    batch_id: int
    row_type: str
    source_id: Optional[str]
    payload: Dict[str, Any]
    status: str
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WhmcsImportBatchOut(BaseModel):
    id: int
    name: str
    status: str
    created_by_user_id: int
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class WhmcsImportBatchDetail(WhmcsImportBatchOut):
    rows: List[WhmcsImportRowOut]
