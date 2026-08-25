from fastapi import FastAPI
from app.core.config import settings


app = FastAPI(
    title="FlyRank Capstone - Image Relevance Engine",
    version="0.1.0",
    description="AI Image Understanding & Content Matching Engine"
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/")
async def root():
    return {"message": "FlyRank Capstone API", "docs": "/docs"}