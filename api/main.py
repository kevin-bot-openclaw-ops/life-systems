"""
Life Systems FastAPI Application
Version: 1.0
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import secrets
import os
from typing import List, Dict, Any

from .routes import jobs, dates, fitness, dashboard, market, actions, insights

app = FastAPI(
    title="Life Systems",
    description="Personal life operating system: Career, Dating, Fitness",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Auth
security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials."""
    correct_username = os.getenv("LS_USER", "jurek")
    correct_password = os.getenv("LS_PASSWORD", "LifeSystems2026!")
    
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        correct_username.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Include routers
app.include_router(jobs.router, prefix="/api", dependencies=[Depends(verify_credentials)])
app.include_router(dates.router, prefix="/api", dependencies=[Depends(verify_credentials)])
app.include_router(fitness.router, prefix="/api", dependencies=[Depends(verify_credentials)])
app.include_router(dashboard.router, prefix="/api", dependencies=[Depends(verify_credentials)])
app.include_router(market.router, prefix="/api", dependencies=[Depends(verify_credentials)])
app.include_router(actions.router, prefix="/api", dependencies=[Depends(verify_credentials)])
app.include_router(insights.router, prefix="/api", dependencies=[Depends(verify_credentials)])

@app.get("/api/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    return {
        "status": "ok",
        "version": "1.0.0"
    }

@app.get("/api/widget")
async def widget_data(username: str = Depends(verify_credentials)):
    """
    iPhone Scriptable widget endpoint.
    Returns minimal JSON for home screen widget.
    """
    # TODO: Calculate from DB
    return {
        "career_score": 72,
        "dating_score": 45,
        "gym_streak": 8,
        "actions_today": 3
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
