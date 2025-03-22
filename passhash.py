from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'])

def hashPassword(password : str) -> str:
    return pwd_context.hash(password)

def verifyPassword(plainPassword: str, hashedPassword: str) -> bool:
    return pwd_context.verify(plainPassword, hashedPassword)