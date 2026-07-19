from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


STUDY_ROOT = Path(__file__).resolve().parents[1] / "docker" / "study-deck"
sys.path.insert(0, str(STUDY_ROOT))

from study_deck.deck import Deck  # noqa: E402
from study_deck.progress import ProgressStore  # noqa: E402


CONTENT = STUDY_ROOT / "content" / "deck.json"


class StudyDeckTests(unittest.TestCase):
    def test_content_is_versioned_and_answers_are_bounded(self) -> None:
        deck = Deck(CONTENT)
        self.assertGreaterEqual(len(deck.questions), 10)
        self.assertGreaterEqual(len(deck.notes), 4)
        self.assertTrue(all(question.answer in question.choices for question in deck.questions.values()))
        self.assertTrue(all(question.source.startswith("docs/") for question in deck.questions.values()))

    def test_duplicate_question_ids_are_rejected(self) -> None:
        payload = json.loads(CONTENT.read_text(encoding="utf-8"))
        payload["questions"].append(payload["questions"][0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deck.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate question id"):
                Deck(path)

    def test_progress_persists_and_incorrect_answers_return_to_box_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "study.db"
            first = ProgressStore(path)
            promoted = first.record("question-one", correct=True, confidence=5)
            self.assertEqual(promoted["box"], 1)
            second = ProgressStore(path)
            self.assertEqual(second.states()["question-one"]["box"], 1)
            reset = second.record("question-one", correct=False, confidence=5)
            self.assertEqual(reset["box"], 0)
            self.assertEqual(reset["attempts"], 2)

    def test_reset_removes_personal_progress_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ProgressStore(Path(directory) / "study.db")
            store.record("question-one", correct=True, confidence=3)
            store.reset()
            self.assertEqual(store.states(), {})

    def test_unseen_questions_are_counted_as_due(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deck = Deck(CONTENT)
            summary = ProgressStore(Path(directory) / "study.db").summary(len(deck.questions))
            self.assertEqual(summary["due"], len(deck.questions))
            self.assertEqual(summary["studied"], 0)

    def test_progress_export_can_restore_a_fresh_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = ProgressStore(Path(directory) / "first.db")
            first.record("question-one", correct=True, confidence=5)
            second = ProgressStore(Path(directory) / "second.db")
            second.restore(first.export())
            self.assertEqual(second.states(), first.states())


if __name__ == "__main__":
    unittest.main()
