import csv
import io
import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ParsedRow:
    douban_id: str | None
    title: str
    imdb_id: str | None
    release_date: str | None
    rating: float | None
    review: str | None
    tagged_date: str | None
    source_url: str | None
    year: int | None


def _normalize_date(raw: str | None) -> str | None:
    """Convert YYYY/M/D or YYYY-MM-DD to YYYY-MM-DD."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _extract_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    m = re.match(r"(\d{4})", date_str)
    return int(m.group(1)) if m else None


def parse_csv(file_content: bytes) -> list[ParsedRow]:
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        release_date = _normalize_date(r.get("上映日期", "").strip())
        tagged_date = _normalize_date(r.get("标记日期", "").strip())
        imdb_id = r.get("IMDb ID", "").strip() or None
        rating_str = r.get("我的评分", "").strip()
        review = r.get("我的评价", "").strip() or None

        rows.append(ParsedRow(
            douban_id=r.get("豆瓣ID", "").strip() or None,
            title=r.get("标题", "").strip(),
            imdb_id=imdb_id,
            release_date=release_date,
            rating=float(rating_str) if rating_str else None,
            review=review,
            tagged_date=tagged_date,
            source_url=r.get("条目链接", "").strip() or None,
            year=_extract_year(release_date),
        ))
    return rows
