import asyncio
from vault.core.database import SessionLocal
from vault.api.coordinator.actions import delete_file

async def main():
    async with SessionLocal() as db:
        success = await delete_file("7fd06937-63ff-4bbe-8995-ce5cbf06e555", db, None)
        print("Success:", success)

asyncio.run(main())
