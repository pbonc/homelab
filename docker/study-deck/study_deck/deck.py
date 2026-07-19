from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Question:
    id: str
    topic: str
    difficulty: str
    prompt: str
    choices: tuple[str, ...]
    answer_index: int
    explanation: str
    source: str
    interview: bool

    @property
    def answer(self) -> str:
        return self.choices[self.answer_index]


@dataclass(frozen=True)
class Note:
    id: str
    topic: str
    title: str
    body: str
    source: str


class Deck:
    def __init__(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0.0":
            raise ValueError("unsupported study deck schema")
        raw_questions = payload.get("questions")
        raw_notes = payload.get("notes")
        if not isinstance(raw_questions, list) or not isinstance(raw_notes, list):
            raise ValueError("study deck requires question and note lists")
        self.questions: dict[str, Question] = {}
        for raw in raw_questions:
            choices = tuple(str(value) for value in raw["choices"])
            answer_index = int(raw["answer_index"])
            if len(choices) < 2 or not 0 <= answer_index < len(choices):
                raise ValueError("question choices or answer index are invalid")
            question = Question(
                id=str(raw["id"]), topic=str(raw["topic"]),
                difficulty=str(raw["difficulty"]), prompt=str(raw["prompt"]),
                choices=choices, answer_index=answer_index,
                explanation=str(raw["explanation"]), source=str(raw["source"]),
                interview=bool(raw.get("interview", False)),
            )
            if question.id in self.questions:
                raise ValueError(f"duplicate question id: {question.id}")
            self.questions[question.id] = question
        self.notes = [
            Note(
                id=str(raw["id"]), topic=str(raw["topic"]),
                title=str(raw["title"]), body=str(raw["body"]),
                source=str(raw["source"]),
            )
            for raw in raw_notes
        ]
