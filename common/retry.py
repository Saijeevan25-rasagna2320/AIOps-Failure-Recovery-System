import asyncio
import httpx

async def retry_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    retries: int = 3,
    timeout: float = 3.0,
    backoff: float = 0.2
):
    for attempt in range(retries):
        try:
            if method == "GET":
                response = await client.get(url, timeout=timeout)
            elif method == "POST":
                response = await client.post(url, timeout=timeout)
            else:
                raise ValueError("Unsupported method")

            return response

        except Exception as e:
            if attempt == retries - 1:
                raise e

            await asyncio.sleep(backoff * (attempt + 1))