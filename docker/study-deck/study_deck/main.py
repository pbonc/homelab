from __future__ import annotations

import os
import random
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from study_deck import __version__
from study_deck.deck import Deck
from study_deck.progress import ProgressStore


class AnswerSubmission(BaseModel):
    question_id: str
    selected: str
    confidence: int = Field(ge=1, le=5)


class ProgressEntry(BaseModel):
    question_id: str = Field(min_length=1)
    box: int = Field(ge=0, le=5)
    due_at: datetime
    attempts: int = Field(ge=0)
    correct: int = Field(ge=0)
    last_answered_at: datetime


class ProgressBackup(BaseModel):
    schema_version: str
    progress: list[ProgressEntry]


APP_ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = Path(os.environ.get("STUDY_DECK_CONTENT", APP_ROOT / "content" / "deck.json"))
DATABASE_PATH = Path(os.environ.get("STUDY_DECK_DATABASE", APP_ROOT / "study.db"))
STATIC_PATH = APP_ROOT / "static"


def create_app(*, deck: Deck | None = None, store: ProgressStore | None = None) -> FastAPI:
    active_deck = deck or Deck(CONTENT_PATH)
    active_store = store or ProgressStore(DATABASE_PATH)
    application = FastAPI(title="Homelab Study Deck", version=__version__)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://192.168.1.23:3000"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_PATH / "index.html")

    @application.get("/app.css", include_in_schema=False)
    def css() -> FileResponse:
        return FileResponse(STATIC_PATH / "app.css", media_type="text/css")

    @application.get("/app.js", include_in_schema=False)
    def javascript() -> FileResponse:
        return FileResponse(STATIC_PATH / "app.js", media_type="text/javascript")

    @application.get("/api/health")
    def health() -> dict[str, object]:
        return {"status": "healthy", "version": __version__, "questions": len(active_deck.questions), "notes": len(active_deck.notes)}

    @application.get("/api/session")
    def session(limit: int = Query(default=5, ge=1, le=20), mode: str = "review") -> dict[str, object]:
        if mode not in {"review", "interview"}:
            raise HTTPException(status_code=422, detail="mode must be review or interview")
        now = datetime.now(timezone.utc)
        states = active_store.states()
        questions = [q for q in active_deck.questions.values() if mode == "review" or q.interview]
        questions.sort(key=lambda q: str(states.get(q.id, {}).get("due_at", "")))
        due = [q for q in questions if q.id not in states or datetime.fromisoformat(str(states[q.id]["due_at"])) <= now]
        selected = due[:limit]
        if len(selected) < limit:
            selected.extend(q for q in questions if q not in selected and q not in due[:limit])
            selected = selected[:limit]
        result = []
        for question in selected:
            choices = list(question.choices)
            random.SystemRandom().shuffle(choices)
            result.append({
                "id": question.id, "topic": question.topic, "difficulty": question.difficulty,
                "prompt": question.prompt, "choices": choices,
                "due": question.id in {item.id for item in due},
            })
        return {"schema_version": "1.0.0", "mode": mode, "count": len(result), "questions": result}

    @application.post("/api/answers")
    def answer(submission: AnswerSubmission) -> dict[str, object]:
        question = active_deck.questions.get(submission.question_id)
        if question is None:
            raise HTTPException(status_code=404, detail="question not found")
        if submission.selected not in question.choices:
            raise HTTPException(status_code=422, detail="selected answer is not a valid choice")
        correct = submission.selected == question.answer
        progress = active_store.record(question.id, correct=correct, confidence=submission.confidence)
        return {
            "question_id": question.id, "correct": correct, "answer": question.answer,
            "explanation": question.explanation, "source": question.source, "progress": progress,
        }

    @application.get("/api/notes")
    def notes(topic: str | None = None) -> dict[str, object]:
        selected = [note for note in active_deck.notes if topic is None or note.topic == topic]
        return {"count": len(selected), "notes": [note.__dict__ for note in selected]}

    @application.get("/api/progress")
    def progress() -> dict[str, object]:
        return active_store.summary(len(active_deck.questions))

    @application.delete("/api/progress", status_code=204)
    def reset_progress() -> None:
        active_store.reset()

    @application.get("/api/progress/export")
    def export_progress() -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "progress": active_store.export(),
        }

    @application.post("/api/progress/restore")
    def restore_progress(backup: ProgressBackup) -> dict[str, int]:
        if backup.schema_version != "1.0.0":
            raise HTTPException(status_code=422, detail="unsupported progress schema version")
        question_ids = [entry.question_id for entry in backup.progress]
        if len(question_ids) != len(set(question_ids)):
            raise HTTPException(status_code=422, detail="duplicate question id in progress backup")
        if set(question_ids) - set(active_deck.questions):
            raise HTTPException(status_code=422, detail="unknown question id in progress backup")
        entries = [entry.model_dump(mode="json") for entry in backup.progress]
        if any(int(entry["correct"]) > int(entry["attempts"]) for entry in entries):
            raise HTTPException(status_code=422, detail="correct count cannot exceed attempts")
        active_store.restore(entries)
        return active_store.summary(len(active_deck.questions))

    return application


app = create_app()
