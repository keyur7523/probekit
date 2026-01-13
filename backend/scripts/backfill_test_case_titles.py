import asyncio
from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models import TestCase


def _make_title(prompt: str) -> str:
    title = prompt.strip().split("\n", 1)[0]
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    return title


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(TestCase))
        test_cases = result.scalars().all()
        updated = 0
        for test_case in test_cases:
            if test_case.title:
                continue
            test_case.title = _make_title(test_case.prompt)
            updated += 1
        if updated:
            await db.commit()
        print(f"Updated {updated} test cases")


if __name__ == "__main__":
    asyncio.run(main())
