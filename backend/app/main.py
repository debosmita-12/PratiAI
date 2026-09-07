from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints, auth

app = FastAPI(title="Railway Block Planner API", version="1.0")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "railway-block-planner"}
