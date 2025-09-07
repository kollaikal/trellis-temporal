from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from typing import Any
import json
import app.config as config

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None

def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_async_engine(
            config.DATABASE_URL,
            pool_pre_ping=False,
            poolclass=NullPool,
        )
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine

def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker

async def execute(sql: str, params: dict | None = None) -> None:
    sm = get_sessionmaker()
    async with sm() as sess:
        await sess.execute(text(sql), params or {})
        await sess.commit()

async def fetchone(sql: str, params: dict | None = None) -> dict | None:
    sm = get_sessionmaker()
    async with sm() as sess:
        res = await sess.execute(text(sql), params or {})
        row = res.mappings().first()
        return dict(row) if row else None

async def fetchall(sql: str, params: dict | None = None) -> list[dict[str, Any]]:
    sm = get_sessionmaker()
    async with sm() as sess:
        res = await sess.execute(text(sql), params or {})
        rows = res.mappings().all()
        return [dict(r) for r in rows]

def json_dumps(obj: Any) -> str:
    return json.dumps(obj)


