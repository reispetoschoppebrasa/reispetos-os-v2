import os
from datetime import datetime,timedelta,timezone
from jose import jwt,JWTError
from passlib.context import CryptContext
from fastapi import Header,HTTPException
KEY=os.getenv("SECRET_KEY","altere-esta-chave");ALG="HS256";pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
def hash_password(x): return pwd.hash(x)
def verify_password(x,h): return pwd.verify(x,h)
def create_token(u,r): return jwt.encode({"sub":u,"role":r,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},KEY,algorithm=ALG)
def current_user(authorization: str=Header(default="")):
    if not authorization.startswith("Bearer "): raise HTTPException(401,"Token ausente")
    try:
        d=jwt.decode(authorization[7:],KEY,algorithms=[ALG]);return {"username":d["sub"],"role":d["role"]}
    except JWTError: raise HTTPException(401,"Token inválido")
