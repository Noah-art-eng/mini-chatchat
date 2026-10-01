"""Conversation、Message History 与 Feedback HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import ConversationUpdateRequest, FeedbackRequest
from auth.dependencies import get_current_user_optional, get_request_user_id
from auth.models import CurrentUser
from db import (
    delete_conversation,
    get_conversation,
    get_conversation_messages,
    list_conversations,
    update_conversation_title,
    update_message_feedback,
)


router = APIRouter()


@router.post("/chat/feedback")
def chat_feedback(
    request: FeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 chat_feedback 的函数职责。"""
    if request.score not in [1, -1]:
        return {
            "error": "score must be 1 or -1"
        }

    updated = update_message_feedback(
        request.message_id,
        request.score,
        request.reason,
        user_id=get_request_user_id(current_user),
    )

    if not updated:
        raise HTTPException(status_code=404, detail="message not found")

    return {
        "message": "feedback saved",
        "message_id": request.message_id,
        "feedback_score": request.score,
        "feedback_reason": request.reason
    }


@router.get("/conversations")
def get_conversations(current_user: CurrentUser = Depends(get_current_user_optional)):
    """负责 get_conversations 的函数职责。"""
    return {
        "conversations": list_conversations(user_id=get_request_user_id(current_user))
    }


@router.get("/conversations/{conversation_id}/messages")
def get_conversation_history(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 get_conversation_history 的函数职责。"""
    user_id = get_request_user_id(current_user)

    if get_conversation(conversation_id, user_id=user_id) is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    return {
        "conversation_id": conversation_id,
        "messages": get_conversation_messages(
            conversation_id,
            user_id=user_id,
        )
    }


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    request: ConversationUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 update_conversation 的函数职责。"""
    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="title cannot be empty"
        )

    conversation = update_conversation_title(
        conversation_id,
        title,
        user_id=get_request_user_id(current_user),
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="conversation not found"
        )

    return {
        "conversation": conversation
    }


@router.delete("/conversations/{conversation_id}")
def remove_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user_optional),
):
    """负责 remove_conversation 的函数职责。"""
    deleted = delete_conversation(
        conversation_id,
        user_id=get_request_user_id(current_user),
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="conversation not found"
        )

    return {
        "message": "conversation deleted",
        "conversation_id": conversation_id
    }
