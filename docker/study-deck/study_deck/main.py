from __future__ import annotations

import os
import random
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from study_deck import __version__
from study_deck.deck import Deck
from study_deck.progress import ProgressStore


class AnswerSubmission(BaseModel):
    question_id: str
    selected: str
    confidence: int = Field(ge=1, le=5)


APP_ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = Path(os.environ.get("STUDY_DECK_CONTENT", APP_ROOT / "content" / "deck.json"))
DATABASE_PATH = Path(os.environ.get("STUDY_DECK_DATABASE", APP_ROOT / "study.db"))
STATIC_PATH = APP_ROOT / "static"


def create_app(*, deck: Deck | None = None, store: ProgressStore | None = None) -> FastAPI:
    active_deck = deck or Deck(CONTENT_PATH)
    active_store = store or ProgressStore(DATABASE_PATH)
    application = FastAPI(title="Homelab Study Deck", version=__version__)

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
        states = active_store.states()
        now = datetime.now(timezone.utc)
        due = sum(datetime.fromisoformat(str(state["due_at"])) <= now for state in states.values())
        attempts = sum(int(state["attempts"]) for state in states.values())
        correct = sum(int(state["correct"]) for state in states.values())
        return {"questions": len(active_deck.questions), "studied": len(states), "due": due, "attempts": attempts, "correct": correct}

    @application.delete("/api/progress", status_code=204)
    def reset_progress() -> None:
        active_store.reset()

    return application


app = create_app()
