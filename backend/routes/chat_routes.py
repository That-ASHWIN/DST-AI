"""
Chat APIs
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Chat"],
)


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="User message",
    )


class ChatResponse(BaseModel):
    response: str
    request_id: str | None = None


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with CIMS SAGE",
)
def chat(request: ChatRequest, http_request: Request):
    request_id = getattr(http_request.state, "request_id", None)
    logger.info(
        "Chat request %s (%d chars)",
        request_id,
        len(request.query),
    )

    chatbot = http_request.app.state.chatbot

    try:
        reply = chatbot.chat(request.query)
        return ChatResponse(
            response=reply,
            request_id=request_id,
        )
    except ValueError as e:
        logger.warning(
            "Chat request %s rejected by chatbot: %s",
            request_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(
            "Chat endpoint failed [request_id=%s]",
            request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        ) from e