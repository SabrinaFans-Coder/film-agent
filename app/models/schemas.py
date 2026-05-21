from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class HistoryMessage(BaseModel):
    role: str          # "user" | "assistant" | "tool"
    content: str
    timestamp: str     # ISO 8601


class SessionInfo(BaseModel):
    session_id: str
    last_preview: str
    first_message: str = ""
    message_count: int
    created_at: str
    updated_at: str
    healthy: bool = True


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]
    total: int
    limit: int
    offset: int


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]


class SyncResultSchema(BaseModel):
    total: int
    new_movies: int
    new_ratings: int
    new_vectors: int
    skipped: int
    tmdb_enriched: int


class RatingItemSchema(BaseModel):
    title: str
    year: int | None = None
    genres: str | None = None
    rating: float | None = None
    review: str | None = None
    tagged_date: str | None = None
    imdb_id: str | None = None
    source_url: str | None = None


class RatingListResponse(BaseModel):
    items: list[RatingItemSchema]
    total: int
    limit: int
    offset: int