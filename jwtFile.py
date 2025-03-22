import jwt
from fastapi import HTTPException, Security, Request
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
        """Extracts token from cookies instead of Authorization header"""
        token = request.cookies.get("access_token")

        if not token:
            raise HTTPException(status_code=403, detail="Not authenticated")

        if token.startswith("Bearer "):  # ✅ Remove "Bearer " if present
            token = token.split("Bearer ")[1]

        return self.decodeToken(token)


    
    