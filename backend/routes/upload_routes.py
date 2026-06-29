import logging, uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from backend.config import ALLOWED_FILE_TYPES, MAX_UPLOAD_SIZE, UPLOAD_DIR
from backend.ingestion.pdf_loader import ingest_pdf
from backend.routes.deps import require_admin
logger=logging.getLogger(__name__); router=APIRouter(prefix="/admin/upload",tags=["Admin Ingestion"],dependencies=[Depends(require_admin)])
@router.post("/pdf")
async def upload_pdf(file:UploadFile=File(...), department:str=Form("general")):
    if not file.filename: raise HTTPException(400,"No filename provided")
    suffix=Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_FILE_TYPES: raise HTTPException(400,"Only PDF files are allowed")
    safe=f"{uuid.uuid4().hex}{suffix}"; path=UPLOAD_DIR/safe; data=await file.read()
    if len(data)>MAX_UPLOAD_SIZE: raise HTTPException(413,"File too large")
    if not data: raise HTTPException(400,"Uploaded file is empty")
    path.write_bytes(data)
    try: chunks=ingest_pdf(path,department=department)
    except Exception as e: path.unlink(missing_ok=True); logger.exception("PDF ingestion failed"); raise HTTPException(500,"Failed to process PDF") from e
    return {"success":True,"filename":file.filename,"stored_as":safe,"department":department,"chunks_indexed":chunks,"message":"PDF uploaded and indexed successfully."}
