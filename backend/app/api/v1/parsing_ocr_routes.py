# backend/app/api/v1/parsing_ocr_routes.py

from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, Body, HTTPException
from backend.app.core.rbac import RequireViewer
from backend.app.services.parsing_ocr_service import ParsingOCRService
from backend.app.schemas.extraction import ParsingResult

router = APIRouter(prefix="/parsing-ocr", tags=["parsing-ocr"])

@router.post("/parse", response_model=ParsingResult, dependencies=[RequireViewer])
async def parse_multipart(
    file: Optional[UploadFile] = File(default=None),
    path: Optional[str] = Form(default=None),
):
    if file is None and not path:
        raise HTTPException(status_code=400, detail="Provide either an uploaded file or a filesystem path.")
    return ParsingOCRService().parse(file=file, path=path)

@router.post("/parse_json", response_model=ParsingResult, dependencies=[RequireViewer])
async def parse_json(payload: Dict[str, Any] = Body(...)):
    path = payload.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="Provide either an uploaded file or a filesystem path.")
    return ParsingOCRService().parse(file=None, path=path)
