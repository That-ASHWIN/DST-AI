"""Chat APIs including streaming endpoint."""
import logging
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
logger=logging.getLogger(__name__); router=APIRouter(tags=["Chat"])
class ChatRequest(BaseModel):
    query:str=Field(...,min_length=1,max_length=4096,description="User message")
    department:str|None=Field("auto",description="Department filter: auto, computer-science, mathematics, mba, general")
class ChatResponse(BaseModel): response:str; request_id:str|None=None; department:str|None=None
@router.post("/chat",response_model=ChatResponse,summary="Chat with CIMS SAGE 2")
def chat(request:ChatRequest,http_request:Request):
    request_id=getattr(http_request.state,"request_id",None); chatbot=http_request.app.state.chatbot
    try: return ChatResponse(response=chatbot.chat(request.query,request.department),request_id=request_id,department=request.department)
    except ValueError as e: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail=str(e)) from e
    except Exception as e: logger.exception("Chat failed"); raise HTTPException(status_code=500,detail="Internal server error") from e
@router.post("/chat/stream",summary="Stream chat response")
def chat_stream(request:ChatRequest,http_request:Request):
    chatbot=http_request.app.state.chatbot
    def gen():
        for chunk in chatbot.stream_chat(request.query,request.department): yield chunk
    return StreamingResponse(gen(),media_type="text/plain; charset=utf-8")
