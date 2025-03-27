from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import chat_routes
from app.services.database import database_service
from contextlib import asynccontextmanager

# Lifespan for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database indexes on startup
    await database_service.create_indexes()
    yield  # Let the app run
    # Optional: Add any cleanup logic here if needed

# Create FastAPI app with lifespan
app = FastAPI(
    title="Chat Summarization API",
    description="An advanced API for chat storage, retrieval, and LLM-powered insights",
    version="1.0.0",
    lifespan=lifespan,  # <-- Add lifespan here
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(chat_routes.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Welcome to Chat Summarization API",
        "version": "1.0.0",
        "endpoints": [
            "/api/v1/chats",
            "/api/v1/chats/summarize",
            "/api/v1/users/{user_id}/chats"
        ]
}
