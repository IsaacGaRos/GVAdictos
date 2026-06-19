"""Topic endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from src.api.models import TopicResponse, TopicDetailResponse, ArticleResponse
from src.core.db import connect
from src.core.paths import DB_PATH

router = APIRouter()


def get_db() -> sqlite3.Connection:
    return connect(DB_PATH)


@router.get("", response_model=list[TopicResponse])
async def list_topics(
    part: str | None = None,
    skip: int = 0,
    limit: int = 75,
    db: sqlite3.Connection = Depends(get_db),
):
    """List topics with optional filtering by part (general/especial)."""
    query = "SELECT * FROM topics WHERE 1=1"
    params = []

    if part in ["general", "especial"]:
        query += " AND part = ?"
        params.append(part)

    query += f" ORDER BY topic_number LIMIT {limit} OFFSET {skip}"

    rows = db.execute(query, params).fetchall()
    result = []

    for row in rows:
        topic = dict(row)
        count = db.execute(
            "SELECT COUNT(DISTINCT article_id) FROM topic_sources WHERE topic_id = ?",
            (topic["id"],),
        ).fetchone()[0]
        topic["articles_count"] = count
        result.append(TopicResponse(**topic))

    return result


@router.get("/{topic_id}", response_model=TopicDetailResponse)
async def get_topic(
    topic_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get topic with its articles."""
    topic = db.execute(
        "SELECT * FROM topics WHERE id = ?",
        (topic_id,),
    ).fetchone()

    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    topic_dict = dict(topic)

    # Get articles for this topic
    articles = db.execute(
        """
        SELECT DISTINCT a.* FROM articles a
        JOIN topic_sources ts ON a.id = ts.article_id
        WHERE ts.topic_id = ?
        ORDER BY a.article_ref
        """,
        (topic_id,),
    ).fetchall()
    topic_dict["articles"] = [dict(a) for a in articles]

    return TopicDetailResponse(**topic_dict)


@router.get("/{topic_id}/articles", response_model=list[ArticleResponse])
async def get_topic_articles(
    topic_id: int,
    skip: int = 0,
    limit: int = 100,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get articles for a specific topic."""
    articles = db.execute(
        """
        SELECT DISTINCT a.* FROM articles a
        JOIN topic_sources ts ON a.id = ts.article_id
        WHERE ts.topic_id = ?
        ORDER BY a.article_ref
        LIMIT ? OFFSET ?
        """,
        (topic_id, limit, skip),
    ).fetchall()

    if not articles:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return [dict(a) for a in articles]
