from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


INTERVALS = (timedelta(minutes=10), timedelta(days=1), timedelta(days=3), timedelta(days=7), timedelta(days=14), timedelta(days=30))


class ProgressStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS question_progress (
                    question_id TEXT PRIMARY KEY,
                    box INTEGER NOT NULL,
                    due_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    correct INTEGER NOT NULL,
                    last_answered_at TEXT NOT NULL
                )"""
            )

    def states(self) -> dict[str, dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM question_progress").fetchall()
        return {row["question_id"]: dict(row) for row in rows}

    def record(self, question_id: str, *, correct: bool, confidence: int) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        states = self.states()
        previous = states.get(question_id)
        old_box = int(previous["box"]) if previous else 0
        if correct:
            new_box = min(5, old_box + 1) if confidence >= 3 else old_box
        else:
            new_box = 0
        due_at = now + INTERVALS[new_box]
        attempts = int(previous["attempts"]) + 1 if previous else 1
        correct_total = int(previous["correct"]) + int(correct) if previous else int(correct)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO question_progress
                   (question_id, box, due_at, attempts, correct, last_answered_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(question_id) DO UPDATE SET
                     box=excluded.box, due_at=excluded.due_at,
                     attempts=excluded.attempts, correct=excluded.correct,
                     last_answered_at=excluded.last_answered_at""",
                (question_id, new_box, due_at.isoformat(), attempts, correct_total, now.isoformat()),
            )
        return {"box": new_box, "due_at": due_at.isoformat(), "attempts": attempts, "correct": correct_total}

    def summary(self, total_questions: int) -> dict[str, int]:
        states = self.states()
        now = datetime.now(timezone.utc)
        due = total_questions - len(states)
        due += sum(datetime.fromisoformat(str(state["due_at"])) <= now for state in states.values())
        return {
            "questions": total_questions,
            "studied": len(states),
            "due": due,
            "attempts": sum(int(state["attempts"]) for state in states.values()),
            "correct": sum(int(state["correct"]) for state in states.values()),
        }

    def export(self) -> list[dict[str, object]]:
        return sorted(self.states().values(), key=lambda state: str(state["question_id"]))

    def restore(self, entries: list[dict[str, object]]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM question_progress")
            connection.executemany(
                """INSERT INTO question_progress
                   (question_id, box, due_at, attempts, correct, last_answered_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (
                        str(entry["question_id"]), int(entry["box"]), str(entry["due_at"]),
                        int(entry["attempts"]), int(entry["correct"]), str(entry["last_answered_at"]),
                    )
                    for entry in entries
                ],
            )

    def reset(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM question_progress")
