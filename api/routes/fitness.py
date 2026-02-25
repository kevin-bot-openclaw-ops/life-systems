"""
Fitness tracking API routes.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import date

router = APIRouter(tags=["fitness"])

class FitnessLog(BaseModel):
    date: date
    completed: bool
    rest_day: bool = False
    notes: str = None

@router.get("/fitness")
async def get_fitness_stats():
    """
    Get gym streak + history.
    """
    # TODO: Calculate streak from DB
    return {
        "current_streak": 0,
        "longest_streak": 0,
        "sessions_this_week": 0,
        "sessions_this_month": 0
    }

@router.post("/fitness/log")
async def log_fitness(log: FitnessLog):
    """
    Log gym session (Done/Rest Day).
    """
    # TODO: Insert into fitness table, recalculate streak
    return {
        "date": log.date.isoformat(),
        "completed": log.completed,
        "rest_day": log.rest_day,
        "new_streak": 1
    }
