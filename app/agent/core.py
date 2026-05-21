import asyncio as _asyncio
import uuid
import sqlite3
from datetime import datetime, timezone
from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
import re
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.config import get_settings
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import tmdb_search
from app.agent.user_profile_tool import get_user_ratings_profile
from app.rag.retriever_tool import create_movie_retriever_tool
from app.db.checkpoint import (
    get_checkpointer,
    upsert_session_meta,
    list_sessions_meta,
    delete_session_meta,
)
from app.models.schemas import SessionListResponse, SessionInfo, HistoryResponse, HistoryMessage
from app.utils.logging import log_event
import httpx as _httpx

DB_PATH = "data/checkpoints.db"
MAX_HISTORY_MESSAGES = 20  # 10 user/assistant turns


class AgentCore:
    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            openai_api_key=settings.DEEPSEEK_API_KEY,
            openai_api_base=settings.DEEPSEEK_BASE_URL,
            temperature=0.7,
        )
        self.tools = [tmdb_search, get_user_ratings_profile]
        retriever_tool = create_movie_retriever_tool()
        if retriever_tool is not None:
            self.tools.append(retriever_tool)
        self._agent = None

    async def _get_agent(self):
        if self._agent is None:
            cp = await get_checkpointer()
            self._agent = create_agent(
                model=self.llm,
                tools=self.tools,
                system_prompt=SYSTEM_PROMPT,
                checkpointer=cp,
                debug=False,
            )
        return self._agent

    async def _trim_history(self, config: dict):
        """Keep last MAX_HISTORY_MESSAGES; extend backward to avoid splitting tool_call from its response."""
        cp = await get_checkpointer()
        tup = await cp.aget_tuple(config)
        if not tup or not tup.checkpoint:
            return
        msgs = tup.checkpoint.get("channel_values", {}).get("messages", [])
        if len(msgs) <= MAX_HISTORY_MESSAGES:
            return
        trimmed = msgs[-MAX_HISTORY_MESSAGES:]
        # If the first trimmed message is a ToolMessage,
        # include its preceding AIMessage(tool_calls) so the pair stays intact
        if trimmed and isinstance(trimmed[0], ToolMessage):
            trim_start = len(msgs) - len(trimmed)
            if trim_start > 0 and isinstance(msgs[trim_start - 1], AIMessage):
                prev_ai = msgs[trim_start - 1]
                if hasattr(prev_ai, "tool_calls") and prev_ai.tool_calls:
                    trimmed = msgs[-(len(trimmed) + 1):]
        await cp.aput(config, {"channel_values": {"messages": trimmed}})

    async def chat(self, message: str, session_id: str | None = None) -> tuple[str, str]:
        is_new = session_id is None or not self._session_exists(session_id)
        if is_new:
            session_id = str(uuid.uuid4())

        if is_new:
            log_event("chat_start", session=session_id[:8], input=message, is_new=True)
        else:
            log_event("chat_start", session=session_id[:8], input=message)

        agent = await self._get_agent()
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": session_id}},
        )

        messages = result.get("messages", [])
        reply = "抱歉，我暂时无法回答。"
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                reply = msg.content
                break

        # Log tool calls and results
        for msg in messages:
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    log_event("tool_call", session=session_id[:8], tool=tc.get("name", "unknown"), args=tc.get("args", {}))
            elif isinstance(msg, ToolMessage):
                log_event("tool_result", session=session_id[:8], tool=msg.name, preview=msg.content[:80] + "..." if len(msg.content) > 80 else msg.content)

        preview = reply[:50] if len(reply) > 50 else reply
        total_count = len(messages)
        movies = _extract_movies_from_messages(messages)
        movies = await _enrich_movies(movies)
        first_msg = message if is_new else ""
        upsert_session_meta(session_id, preview, total_count, movies, first_message=first_msg)
        await self._trim_history({"configurable": {"thread_id": session_id}})

        log_event("chat_done", session=session_id[:8], msg_count=total_count, movies_found=len(movies), reply_preview=preview)
        return reply, session_id

    def _session_exists(self, session_id: str) -> bool:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT 1 FROM sessions_meta WHERE session_id = ?", (session_id,)
        ).fetchone()
        conn.close()
        return row is not None

    def list_sessions(self, limit: int = 20, offset: int = 0) -> SessionListResponse:
        sessions, total = list_sessions_meta(limit, offset)
        return SessionListResponse(
            sessions=[
                SessionInfo(
                    session_id=s["session_id"],
                    last_preview=s.get("first_message") or s["last_preview"],
                    first_message=s.get("first_message", ""),
                    message_count=s["message_count"],
                    created_at=s["created_at"],
                    updated_at=s["updated_at"],
                    healthy=self._check_session_health(s["session_id"]),
                )
                for s in sessions
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def _check_session_health(self, session_id: str) -> bool:
        """Return False if the session has orphaned ToolMessages (unusable state)."""
        import asyncio as _asyncio_mod
        try:
            tup = _asyncio_mod.run(self.checkpointer.aget_tuple(
                {"configurable": {"thread_id": session_id}}
            ))
        except Exception:
            return True  # can't check, assume healthy
        if not tup or not tup.checkpoint:
            return True
        msgs = tup.checkpoint.get("channel_values", {}).get("messages", [])
        if not msgs:
            return True
        # If the first message is a ToolMessage, it's orphaned (tool_call missing)
        if isinstance(msgs[0], ToolMessage):
            return False
        # Also check for standalone ToolMessages not preceded by AIMessage(tool_calls)
        for i, msg in enumerate(msgs):
            if isinstance(msg, ToolMessage):
                if i == 0 or not (isinstance(msgs[i - 1], AIMessage) and hasattr(msgs[i - 1], "tool_calls") and msgs[i - 1].tool_calls):
                    return False
        return True

    async def get_history(self, session_id: str) -> HistoryResponse:
        cp = await get_checkpointer()
        config = {"configurable": {"thread_id": session_id}}
        tup = await cp.aget_tuple(config)
        if tup is None:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

        channel_values = tup.checkpoint.get("channel_values", {})
        raw_messages = channel_values.get("messages", [])

        messages = []
        for msg in raw_messages:
            role = _get_message_role(msg)
            ts = getattr(msg, "timestamp", None)
            if ts is None:
                ts = datetime.now(timezone.utc).isoformat()
            elif hasattr(ts, "isoformat"):
                ts = ts.isoformat()
            messages.append(HistoryMessage(role=role, content=msg.content, timestamp=str(ts)))

        return HistoryResponse(session_id=session_id, messages=messages)

    async def delete_session(self, session_id: str) -> bool:
        cp = await get_checkpointer()
        await cp.adelete_thread(session_id)
        delete_session_meta(session_id)
        return True

    async def stream_chat(self, message: str, session_id: str):
        """Stream chat, yielding {"type": "token"|"done", "content"|"reply": str}."""
        config = {"configurable": {"thread_id": session_id}}
        collected_content = ""
        is_new = not self._session_exists(session_id)
        if is_new:
            log_event("chat_start", session=session_id[:8], input=message, is_new=True)
        else:
            log_event("chat_start", session=session_id[:8], input=message)

        agent = await self._get_agent()
        async for chunk in agent.astream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="messages",
            version="v1",
        ):
            if isinstance(chunk, tuple):
                msg = chunk[0]
            else:
                msg = chunk
            if isinstance(msg, AIMessage) and msg.content:
                new_tokens = msg.content[len(collected_content):]
                if new_tokens:
                    collected_content = msg.content
                    yield {"type": "token", "content": new_tokens}

        preview = collected_content[:50] if len(collected_content) > 50 else collected_content
        # Use async checkpointer to reliably get final message count and movies
        cp = await get_checkpointer()
        tup = await cp.aget_tuple(config)
        if tup and tup.checkpoint:
            channel_msgs = tup.checkpoint.get("channel_values", {}).get("messages", [])
            msg_count = len(channel_msgs)
            movies = _extract_movies_from_messages(channel_msgs)
            movies = await _enrich_movies(movies)
            for msg in channel_msgs:
                if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        log_event("tool_call", session=session_id[:8], tool=tc.get("name", "unknown"), args=tc.get("args", {}))
                elif isinstance(msg, ToolMessage):
                    log_event("tool_result", session=session_id[:8], tool=msg.name, preview=msg.content[:80] + "..." if len(msg.content) > 80 else msg.content)
        else:
            msg_count = 2
            movies = []
        first_msg = message if is_new else ""
        upsert_session_meta(session_id, preview, msg_count, movies, first_message=first_msg)
        await self._trim_history(config)

        log_event("chat_done", session=session_id[:8], msg_count=msg_count, movies_found=len(movies), reply_preview=preview)
        yield {"type": "done", "reply": collected_content or "抱歉，我暂时无法回答。"}


def _extract_movies_from_messages(messages: list) -> list[dict]:
    """Extract movie info from ToolMessage (tmdb_search results) and AIMessage mentions."""
    movies = []
    seen_titles = set()

    for msg in messages:
        content = msg.content if hasattr(msg, "content") else ""
        if not content:
            continue

        if isinstance(msg, ToolMessage):
            # Parse all "--- 结果 N ---" blocks from tmdb_search output
            blocks = re.split(r"--- 结果 \d+ ---", content)
            for block in blocks:
                title_match = re.search(r"片名：(.+)", block)
                rating_match = re.search(r"评分：([\d.]+)", block)
                genres_match = re.search(r"类型：(.+)", block)

                if title_match:
                    title = title_match.group(1).strip()
                    if title and title != "未知" and title not in seen_titles:
                        seen_titles.add(title)
                        genres = []
                        if genres_match:
                            genres = [g.strip() for g in genres_match.group(1).split("、") if g.strip()]
                        movies.append({
                            "title": title,
                            "tmdb_rating": float(rating_match.group(1)) if rating_match else None,
                            "genres": genres,
                        })

        elif isinstance(msg, AIMessage):
            # Fallback: catch 《Movie Title》 patterns in assistant replies
            titles = re.findall(r"《(.+?)》", content)
            for title in titles:
                title = title.strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    movies.append({
                        "title": title,
                        "tmdb_rating": None,
                        "genres": [],
                    })

    return movies


async def _enrich_movies(movies: list[dict]) -> list[dict]:
    """Fill in rating/genres for movies without structured data (AIMessage fallback)."""
    needs_enrich = [m for m in movies if not m.get("genres")]
    if not needs_enrich:
        return movies

    settings = get_settings()
    params_base = {"api_key": settings.TMDB_API_KEY, "language": "zh-CN"}
    title_to_data = {}

    async with _httpx.AsyncClient(
        base_url=settings.TMDB_BASE_URL, timeout=10.0
    ) as client:

        async def _lookup(movie):
            title = movie["title"]
            resp = await client.get("/search/movie", params={**params_base, "query": title})
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if results:
                detail = await client.get(f"/movie/{results[0]['id']}", params=params_base)
                detail.raise_for_status()
                data = detail.json()
                # Verify match relevance to filter out false positives
                tmdb_title = data.get("title", "")
                if tmdb_title.lower() == title.lower() or title.lower() in tmdb_title.lower() or tmdb_title.lower() in title.lower():
                    genres = [g["name"] for g in data.get("genres", [])]
                    title_to_data[title] = {
                        "tmdb_rating": data.get("vote_average"),
                        "genres": genres,
                    }
                else:
                    title_to_data[title] = {}
            else:
                title_to_data[title] = {}  # no match

        await _asyncio.gather(
            *(_lookup(m) for m in needs_enrich), return_exceptions=True
        )

    for movie in movies:
        if not movie.get("genres") and movie["title"] in title_to_data:
            extra = title_to_data[movie["title"]]
            if extra:
                movie["tmdb_rating"] = extra.get("tmdb_rating")
                movie["genres"] = extra.get("genres", [])

    # Filter out non-movie entries: 《》 fallback that TMDB couldn't match
    movies = [m for m in movies if m.get("genres") or m.get("tmdb_rating") is not None]
    return movies


def _get_message_role(msg) -> str:
    type_name = type(msg).__name__
    if "Human" in type_name:
        return "user"
    elif "AI" in type_name:
        return "assistant"
    elif "Tool" in type_name:
        return "tool"
    return "unknown"
