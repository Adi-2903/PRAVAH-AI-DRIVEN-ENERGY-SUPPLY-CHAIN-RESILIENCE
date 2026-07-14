import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")

supabase = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not supabase:
        class MockUser:
            id = "mock-user-id"
            email = "demo@pravah.gov.in"
        return MockUser()
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        response = supabase.auth.get_user(token)
        if not response or not response.user:
            raise Exception("Invalid user")
        return response.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
