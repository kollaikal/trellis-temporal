import asyncio, pathlib
from sqlalchemy import text
from app.db import get_engine

def _split_sql(sql: str) -> list[str]:
    # naive split by semicolon; ignores semicolons in literals (not present in our schema)
    parts = [s.strip() for s in sql.split(";")]
    return [p for p in parts if p]

async def main():
    engine = get_engine()
    sql_path = pathlib.Path(__file__).parent / "migrations" / "001_init.sql"
    sql = sql_path.read_text()
    stmts = _split_sql(sql)
    async with engine.begin() as conn:
        for stmt in stmts:
            await conn.execute(text(stmt))
    print("Migration applied.")

if __name__ == "__main__":
    asyncio.run(main())


