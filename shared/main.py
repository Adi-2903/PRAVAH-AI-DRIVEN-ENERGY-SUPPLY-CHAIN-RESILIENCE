# shared/main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])

app = FastAPI(title="Pravah Shared Backend")


@app.get("/health")
def health():
    return {"status": "ok"}


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/signup")
def signup(payload: SignupRequest):
    try:
        result = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
        return {"user_id": result.user.id, "email": result.user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(payload: LoginRequest):
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
        return {"access_token": result.session.access_token, "user_id": result.user.id}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
