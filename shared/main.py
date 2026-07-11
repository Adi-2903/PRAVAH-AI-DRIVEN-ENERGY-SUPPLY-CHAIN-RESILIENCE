# shared/main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY")
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)
else:
    supabase = None


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Pravah Shared Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from shared.procurement_router import router as procurement_router
app.include_router(procurement_router)


from datetime import datetime
from shared.db.knowledge_graph import build_supply_chain_graph

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/system-status")
def system_status():
    status = {
        "data_sources": {},
        "database": {"connected": False, "row_counts": {}},
        "knowledge_graph": {"built_from_db": False, "nodes": 0, "edges": 0, "last_built_at": None},
        "schemas_validated": True
    }
    
    if supabase:
        status["database"]["connected"] = True
        try:
            # Query data_sources
            res = supabase.table("data_sources").select("*").execute()
            if res.data:
                for row in res.data:
                    name = row["name"].replace("_api", "")
                    status["data_sources"][name] = {
                        "status": "live" if row.get("is_live") else "fallback",
                        "last_synced_at": row.get("last_synced")
                    }
            
            # Row counts
            for table in ["suppliers", "corridors", "refineries", "ships", "risk_events"]:
                try:
                    res_count = supabase.table(table).select("*", count="exact").limit(1).execute()
                    status["database"]["row_counts"][table] = res_count.count
                except:
                    status["database"]["row_counts"][table] = 0
        except Exception as e:
            print("Status fetch error:", e)
    else:
        # Return fallback statuses if no DB connection
        status["data_sources"] = {
            "eia": {"status": "fallback", "last_synced_at": None},
            "gdelt": {"status": "fallback", "last_synced_at": None},
            "aisstream": {"status": "fallback", "last_synced_at": None},
            "ofac": {"status": "fallback", "last_synced_at": None}
        }
            
    # Knowledge graph
    try:
        G = build_supply_chain_graph()
        status["knowledge_graph"] = {
            "built_from_db": status["database"]["connected"],
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "last_built_at": datetime.now().isoformat() + "Z"
        }
    except Exception as e:
        print("Graph build error:", e)
        
    return status


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/signup")
def signup(payload: SignupRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase is not configured on this instance.")
    try:
        result = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
        return {"user_id": result.user.id, "email": result.user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(payload: LoginRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase is not configured on this instance.")
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
        return {"access_token": result.session.access_token, "user_id": result.user.id}
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")
