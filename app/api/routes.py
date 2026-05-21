import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import (
    ChatRequest, ChatResponse,
    SessionListResponse, HistoryResponse,
    SyncResultSchema, RatingItemSchema, RatingListResponse,
)
from app.agent.core import AgentCore
from app.services.excel_report import export_session_excel, export_stats_excel
from app.services.sync_service import sync_user_ratings
from app.services.movie_store import MovieStore

router = APIRouter()
agent_core = AgentCore()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    reply, session_id = await agent_core.chat(
        message=request.message,
        session_id=request.session_id,
    )
    return ChatResponse(reply=reply, session_id=session_id)


@router.get("/chat/stream")
async def chat_stream(message: str, session_id: str | None = None):
    async def event_generator():
        sid = session_id
        if sid is None or not agent_core._session_exists(sid):
            sid = str(uuid.uuid4())
        yield {"event": "session", "data": sid}

        async for chunk in agent_core.stream_chat(message, sid):
            if chunk["type"] == "token":
                yield {"event": "token", "data": chunk["content"]}
            elif chunk["type"] == "done":
                yield {"event": "done", "data": chunk["reply"]}

    return EventSourceResponse(event_generator())


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(limit: int = 20, offset: int = 0) -> SessionListResponse:
    return agent_core.list_sessions(limit=limit, offset=offset)


@router.get("/sessions/{session_id}/messages", response_model=HistoryResponse)
async def get_session_messages(session_id: str) -> HistoryResponse:
    return await agent_core.get_history(session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    await agent_core.delete_session(session_id)
    return {"detail": "deleted"}


@router.get("/export/session/{session_id}")
async def export_session(session_id: str):
    data = await export_session_excel(session_id)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=chat_{session_id}.xlsx"},
    )


@router.get("/export/stats")
async def export_stats():
    data = export_stats_excel()
    date_str = datetime.now().strftime("%Y%m%d")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=film_stats_{date_str}.xlsx"},
    )


@router.post("/api/ratings/import", response_model=SyncResultSchema)
async def import_ratings(
    file: UploadFile = File(...),
    user_id: str = Form("default"),
):
    content = await file.read()
    result = await sync_user_ratings(content, user_id)
    return result


@router.get("/api/ratings", response_model=RatingListResponse)
async def list_ratings(
    user_id: str = Query("default"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_rating: int | None = Query(None, ge=1, le=5),
    sort: str = Query("created_at", pattern="^(created_at|rating)$"),
    search: str | None = Query(None),
):
    store = MovieStore()
    rows, total = store.list_ratings_with_filter(
        user_id, limit, offset, min_rating=min_rating, sort_by=sort, search=search,
    )
    return RatingListResponse(
        items=[
            RatingItemSchema(
                title=r["title"],
                year=r.get("movie_year"),
                genres=r.get("genres"),
                rating=float(r["rating"]) if r.get("rating") else None,
                review=r.get("review"),
                tagged_date=r.get("tagged_date"),
                imdb_id=r.get("imdb_id"),
                source_url=r.get("source_url"),
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.put("/api/ratings/{imdb_id}")
async def update_rating(
    imdb_id: str,
    user_id: str = Query("default"),
    rating: float | None = Query(None, ge=0, le=5),
    review: str | None = Query(None),
):
    store = MovieStore()
    store.update_rating(user_id, imdb_id, rating=rating, review=review)
    return {"detail": "updated"}


@router.delete("/api/ratings/{imdb_id}")
async def delete_rating(
    imdb_id: str,
    user_id: str = Query("default"),
):
    store = MovieStore()
    deleted = store.delete_rating(user_id, imdb_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="rating not found")
    return {"detail": "deleted"}
