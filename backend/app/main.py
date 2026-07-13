from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import agent_router, interactions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="HCP CRM — Log Interaction Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router.router)
app.include_router(interactions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
