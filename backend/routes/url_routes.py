import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from backend.ingestion.url_loader import ingest_url
from backend.routes.deps import require_admin
logger=logging.getLogger(__name__); router=APIRouter(prefix="/admin/upload",tags=["Admin Ingestion"],dependencies=[Depends(require_admin)])
class URLRequest(BaseModel): url:HttpUrl; department:str="general"
@router.post("/url")
async def upload_url(request:URLRequest):
    try:
        chunks=ingest_url(str(request.url),department=request.department)
        if chunks==0: raise HTTPException(422,"No content could be extracted")
        return {"success":True,"url":str(request.url),"department":request.department,"chunks_indexed":chunks,"message":"URL indexed successfully."}
    except HTTPException: raise
    except ValueError as e: raise HTTPException(400,str(e)) from e
    except Exception as e: logger.exception("URL ingestion failed"); raise HTTPException(500,"Failed to fetch or process URL") from e
