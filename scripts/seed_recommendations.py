import json
from tortoise import Tortoise
from app.models.recommendations import Recommendation

async def seed():
    with open("init-db/03-seed-recommendations.json") as f:
        data = json.load(f)

    for item in data:
        await Recommendation.create(
            disease_code=item["disease_code"],
            category=item["category"],
            content=item["content"],
            source=item["source"],
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())