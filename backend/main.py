"""
Main entry point for running the FastAPI application.
"""

import uvicorn
from app.api import app
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )