import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Create a dummy file
        files = {'file': ('test.txt', b'Hello world', 'text/plain')}
        # Upload
        resp = await client.post("http://localhost:8000/files/upload", files=files)
        print("Upload Status:", resp.status_code)
        print("Upload Response:", resp.text)
        
        # List
        resp = await client.get("http://localhost:8000/files/")
        print("List Status:", resp.status_code)
        print("List Response:", resp.text)

asyncio.run(main())
