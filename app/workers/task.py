"""
Background task runner using FastAPI BackgroundTasks.
For production, replace with Celery + Redis or Supabase Edge Functions.
"""
import uuid
from app.agents.background_organizer import BackgroundOrganizer


def run_background_organizer(
    organizer: BackgroundOrganizer,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
) -> None:
    """Callable passed to FastAPI BackgroundTasks."""
    organizer.run(project_id, run_id)