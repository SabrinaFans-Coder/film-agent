from langchain_core.tools.retriever import create_retriever_tool
from langchain_core.tools import BaseTool
from app.rag.embeddings import get_embeddings
from app.rag.vector_store import load_vector_store


def create_movie_retriever_tool() -> BaseTool | None:
    embeddings = get_embeddings()
    vector_store = load_vector_store(embeddings)
    if vector_store is None:
        return None

    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    return create_retriever_tool(
        retriever,
        name="search_movie_knowledge",
        description=(
            "语义搜索电影知识库。当用户询问以下类型问题时使用此工具：\n"
            "- 推荐某类型或某风格的电影（如'推荐几部烧脑的科幻片'）\n"
            "- 寻找类似某部电影的其他影片（如'有没有类似盗梦空间的电影'）\n"
            "- 按主题或关键词搜索电影（如'关于人工智能的电影有哪些'）\n"
            "查询参数应是语义描述，而非精确片名（精确片名用 tmdb_search）"
        ),
    )
