from fastapi import FastAPI
from app.core.config import settings
from app.api.suggestions import router as suggestions_router


app = FastAPI(
    title="FlyRank Capstone - Image Relevance Engine",
    version="0.1.0",
    description="AI Image Understanding & Content Matching Engine"
)

app.include_router(suggestions_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/")
async def root():
    return {"message": "FlyRank Capstone API", "docs": "/docs"}