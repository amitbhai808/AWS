import jwt

token = jwt.encode({"sub": "user_123"}, "secret", algorithm="HS256")
try:
    payload = jwt.decode(token, options={"verify_signature": False})
    print(payload.get("sub"))
except Exception as e:
    print("Error:", e)
