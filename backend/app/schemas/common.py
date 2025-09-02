from pydantic import BaseModel, Field
from typing import Optional

class ErrorResponse(BaseModel):
    detail: str

class Pagination(BaseModel):
    offset: int = 0
    limit: int = 10
    total: Optional[int] = None

class PathInfo(BaseModel):
    id: str
    path: str = Field(description="Filesystem path to the document/section")
