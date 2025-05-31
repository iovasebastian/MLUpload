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
            'exp': now + timedelta(minutes = 120),
            'iat': now,
            'sub': str(userId),
            'role': role
        }
        print(f"Encoding Payload: {payload}")
        return jwt.encode(payload, self.secret, algorithm="HS256")
    
    def decodeToken(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            print(f"Decoded Payload: {payload}") 
            return {"id": int(payload["sub"]), "role": payload["role"]} 
        except jwt.ExpiredSignatureError:
            print("Token Expired!") 
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            print(f"Invalid Token: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid Token")


    def authWrapper(self, request: Request):
        print("authWrapper triggered")
        auth = request.headers.get("Authorization")
        print("Header received:", auth)
        if not auth or not auth.startswith("Bearer "):
            raise HTTPException(status_code=403, detail="Not authenticated")
        token = auth.split("Bearer ")[1]
        return self.decodeToken(token)


    
    