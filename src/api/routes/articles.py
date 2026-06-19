"""Article endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3

from src.api.models import ArticleResponse, ArticleDetailResponse
from src.core.db import connect
from src.core.paths import DB_PATH

router = APIRouter()


def get_db() -> sqlite3.Connection:
    return connect(DB_PATH)


@router.get("", response_model=list[ArticleResponse])
async def list_articles(
    law_id: int | None = None,
    skip: int = 0,
    limit: int = 50,
    db: sqlite3.Connection = Depends(get_db),
):
    """List articles with optional filtering."""
    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if law_id:
        query += " AND law_id = ?"
        params.append(law_id)

    query += f" LIMIT {limit} OFFSET {skip}"

    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@router.get("/{article_id}", response_model=ArticleDetailResponse)
async def get_article(
    article_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get article with insights and related articles."""
    article = db.execute(
        "SELECT * FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    article_dict = dict(article)

    # Get insights
    insights = db.execute(
        """
        SELECT id, insight_type, content, model, requiere_revision, validation_status
        FROM ai_article_insights
        WHERE article_id = ? AND validation_status = 'validado'
        """,
        (article_id,),
    ).fetchall()
    article_dict["insights"] = [dict(i) for i in insights]

    # Get related articles
    related = db.execute(
        """
        SELECT a.id, a.article_ref, a.title FROM article_relations ar
        JOIN articles a ON ar.to_article_id = a.id
        WHERE ar.from_article_id = ?
        LIMIT 5
        """,
        (article_id,),
    ).fetchall()
    article_dict["related"] = [dict(r) for r in related]

    return ArticleDetailResponse(**article_dict)


@router.get("/{article_id}/insights")
async def get_article_insights(
    article_id: int,
    insight_type: str | None = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get AI insights for an article."""
    query = """
        SELECT id, insight_type, content, model, requiere_revision, validation_status
        FROM ai_article_insights
        WHERE article_id = ?
    """
    params = [article_id]

    if insight_type:
        query += " AND insight_type = ?"
        params.append(insight_type)

    rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]
