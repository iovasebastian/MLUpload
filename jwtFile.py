import jwt
from fastapi import HTTPException, Security, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta, timezone

class AuthHandler():
    security = HTTPBearer()
    secret = 'SECRET'

    def encodeToken(self, userId, role):
        now = datetime.now(timezone.utc)
        payload = {
            'exp': now + timedelta(minutes = 60),  # ✅ Token lasts 1 hour
            'iat': now,
            'sub': str(userId),
            'role': role
        }
        print(f"✅ Encoding Payload: {payload}")  # ✅ Debugging
        return jwt.encode(payload, self.secret, algorithm="HS256")
    def decodeToken(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            print(f"✅ Decoded Payload: {payload}")  # ✅ Debugging
            return {"id": int(payload["sub"]), "role": payload["role"]}  # 🔹 FIX: Convert sub back to int
        except jwt.ExpiredSignatureError:
            print("❌ Token Expired!")  # ✅ Debugging
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid Token: {str(e)}")  # ✅ Debugging
            raise HTTPException(status_code=401, detail="Invalid Token")


    def authWrapper(self, request: Request):
        print("🔥 authWrapper triggered")
        auth = request.headers.get("Authorization")
        print("🔑 Header received:", auth)
        if not auth or not auth.startswith("Bearer "):
            raise HTTPException(status_code=403, detail="Not authenticated")
        token = auth.split("Bearer ")[1]
        return self.decodeToken(token)


    
    