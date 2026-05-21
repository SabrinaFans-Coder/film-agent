from pathlib import Path
from langchain_chroma import Chroma


def load_vector_store(embeddings, persist_dir="data/chroma") -> Chroma | None:
    path = Path(persist_dir)
    if not path.exists() or not any(path.iterdir()):
        print(f"索引目录 '{persist_dir}' 为空或不存在，请先运行 scripts/build_index.py")
        return None
    return Chroma(
        persist_directory=str(path),
        embedding_function=embeddings,
    )
