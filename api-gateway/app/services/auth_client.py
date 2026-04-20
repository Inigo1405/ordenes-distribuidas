import httpx
from fastapi import HTTPException
from ..config import AUTH_URL

async def send_auth(user_data=None, type='get', endpoint="/health"):
  for attempt in range(2): 
    try:
      async with httpx.AsyncClient(timeout=2.0) as client:
        if type == 'post':
          r = await client.post(
            AUTH_URL+'internal'+endpoint,
            json=user_data
          )
        else:
          r = await client.get(
            AUTH_URL+'internal'+endpoint
          )
        return r.json()

    except httpx.RequestError as e:
      if attempt == 1:
        raise HTTPException(status_code=503, detail=f"Auth service unreachable: {e}")
      
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)