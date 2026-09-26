import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)

def get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str | None:
    print(f"DEBUG AUTH: credentials present = {bool(credentials)}")
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        print(f"DEBUG AUTH: Decoded user_id = {user_id}")
        return user_id
    except Exception as e:
        print(f"DEBUG AUTH: Exception decoding JWT: {e}")
        return None

