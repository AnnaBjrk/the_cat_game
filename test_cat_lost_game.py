import json
import tempfile
import unittest
from pathlib import Path

from cat_lost_game import (
    ContentError,
    GameState,
    Outcome,
    Phase,
    load_content,
    new_game,
    step,
)

MIN_QUESTIONS = 10
CHOICES_PER_QUESTION = 4
STORY_KEYS = (
    "start_story",
    "blocked",
    "free_descriptions",
    "fetch",
    "leave",
    "question_intro",
    "question_correct",
    "question_wrong",
    "witch_correct",
    "witch_wrong",
    "witch_no_cake",
    "home",
)


def make_question(number=1):
    return {
        "question": f"Fråga {number}?",
        "choices": ["Ett", "Två", "Tre", "Fyra"],
        "answer": "Två",
    }


def make_questions():
    return [make_question(number) for number in range(MIN_QUESTIONS)]


def make_story():
    return {key: "text" for key in STORY_KEYS}


class ContentFilesTest(unittest.TestCase):
    def test_question_file_meets_requirements(self):
        questions = load_content().questions

        self.assertGreaterEqual(len(questions), MIN_QUESTIONS)
        for question in questions:
            self.assertEqual(len(question["choices"]), CHOICES_PER_QUESTION)
            self.assertIn(question["answer"], question["choices"])

    def test_story_file_has_all_texts(self):
        story = load_content().story

        for key in STORY_KEYS:
            self.assertIn(key, story)


class LoadContentTest(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.questions_path = Path(temp_dir.name) / "questions.json"
        self.story_path = Path(temp_dir.name) / "story.json"
        self.write_files(make_questions(), make_story())

    def write_files(self, questions, story):
        self.questions_path.write_text(json.dumps(questions), encoding="utf-8")
        self.story_path.write_text(json.dumps(story), encoding="utf-8")

    def load(self):
        return load_content(self.questions_path, self.story_path)

    def test_valid_files_load(self):
        content = self.load()

        self.assertEqual(content.questions, make_questions())
        self.assertEqual(content.story, make_story())

    def test_missing_file_names_the_file(self):
        self.story_path.unlink()

        with self.assertRaisesRegex(ContentError, "story.json"):
            self.load()

    def test_invalid_json_names_the_file(self):
        self.questions_path.write_text("[{", encoding="utf-8")

        with self.assertRaisesRegex(ContentError, "questions.json"):
            self.load()


class MovementTest(unittest.TestCase):
    def test_game_starts_at_start(self):
        state = new_game()

        self.assertEqual(state.position, (0, 0))
        self.assertEqual(state.discovered, {(0, 0)})
        self.assertEqual(state.phase, Phase.MOVE)

    def test_each_direction_moves_one_step(self):
        for start, command, expected in [
            ((1, 1), "upp", (0, 1)),
            ((1, 0), "ner", (2, 0)),
            ((1, 1), "vänster", (1, 0)),
            ((1, 0), "höger", (1, 1)),
        ]:
            with self.subTest(command=command):
                outcome, state = step(GameState(position=start), command)

                self.assertEqual(outcome, Outcome.MOVED)
                self.assertEqual(state.position, expected)

    def test_visited_square_is_discovered(self):
        _, state = step(new_game(), "höger")

        self.assertIn((0, 1), state.discovered)

    def test_edge_of_map_stops_the_cat(self):
        for command in ["upp", "vänster"]:
            with self.subTest(command=command):
                outcome, state = step(new_game(), command)

                self.assertEqual(outcome, Outcome.BLOCKED)
                self.assertEqual(state.position, (0, 0))
                self.assertEqual(state.discovered, {(0, 0)})

    def test_edge_of_map_stops_the_cat_at_the_far_side(self):
        for position, command in [((4, 1), "ner"), ((1, 4), "höger")]:
            with self.subTest(command=command):
                outcome, state = step(GameState(position=position), command)

                self.assertEqual(outcome, Outcome.BLOCKED)
                self.assertEqual(state.position, position)

    def test_blocked_square_stops_the_cat_but_is_discovered(self):
        outcome, state = step(GameState(position=(1, 1)), "höger")

        self.assertEqual(outcome, Outcome.BLOCKED)
        self.assertEqual(state.position, (1, 1))
        self.assertIn((1, 2), state.discovered)

    def test_invalid_command_does_not_move_the_cat(self):
        outcome, state = step(new_game(), "hoppa")

        self.assertEqual(outcome, Outcome.INVALID_COMMAND)
        self.assertEqual(state.position, (0, 0))

    def test_commands_ignore_case_and_surrounding_spaces(self):
        for command, expected in [("  HÖGER ", (1, 1)), (" Vänster  ", (1, 0))]:
            with self.subTest(command=command):
                start = (1, 0) if "HÖGER" in command else (1, 1)
                _, state = step(GameState(position=start), command)

                self.assertEqual(state.position, expected)

    def test_quit_ends_the_game(self):
        outcome, state = step(new_game(), " AVSLUTA ")

        self.assertEqual(outcome, Outcome.QUIT)
        self.assertEqual(state.phase, Phase.QUIT)


if __name__ == "__main__":
    unittest.main()
