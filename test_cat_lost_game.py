import json
import random
import tempfile
import unittest
from pathlib import Path

from cat_lost_game import (
    CAKES,
    FAVORITE_CAKE,
    FETCH_POSITION,
    HOME_POSITION,
    LEAVE_POSITION,
    START_POSITION,
    ContentError,
    GRID,
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


def make_game(position=(0, 0), seed=1):
    state = new_game(make_questions(), random.Random(seed))
    state.position = position
    return state


def correct_answer(state):
    question = state.current_question
    return str(question["choices"].index(question["answer"]) + 1)


def wrong_answer(state):
    question = state.current_question
    return str((question["choices"].index(question["answer"]) + 1) % 4 + 1)


def choose_cake(state, cake):
    return step(state, str(state.cake_choices.index(cake) + 1))


def enter_fetch(inventory=()):
    state = make_game((0, 3))
    state.inventory = list(inventory)
    _, state = step(state, "höger")
    return state


def enter_leave(inventory=()):
    state = make_game((2, 3))
    state.inventory = list(inventory)
    return step(state, "ner")


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
        state = make_game()

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
                outcome, state = step(make_game(start), command)

                self.assertEqual(outcome, Outcome.MOVED)
                self.assertEqual(state.position, expected)

    def test_visited_square_is_discovered(self):
        _, state = step(make_game(),"höger")

        self.assertIn((0, 1), state.discovered)

    def test_edge_of_map_stops_the_cat(self):
        for command in ["upp", "vänster"]:
            with self.subTest(command=command):
                outcome, state = step(make_game(),command)

                self.assertEqual(outcome, Outcome.BLOCKED)
                self.assertEqual(state.position, (0, 0))
                self.assertEqual(state.discovered, {(0, 0)})

    def test_edge_of_map_stops_the_cat_at_the_far_side(self):
        for position, command in [((4, 1), "ner"), ((1, 4), "höger")]:
            with self.subTest(command=command):
                outcome, state = step(make_game(position), command)

                self.assertEqual(outcome, Outcome.BLOCKED)
                self.assertEqual(state.position, position)

    def test_blocked_square_stops_the_cat_but_is_discovered(self):
        outcome, state = step(make_game((1, 1)), "höger")

        self.assertEqual(outcome, Outcome.BLOCKED)
        self.assertEqual(state.position, (1, 1))
        self.assertIn((1, 2), state.discovered)

    def test_invalid_command_does_not_move_the_cat(self):
        outcome, state = step(make_game(),"hoppa")

        self.assertEqual(outcome, Outcome.INVALID_COMMAND)
        self.assertEqual(state.position, (0, 0))

    def test_commands_ignore_case_and_surrounding_spaces(self):
        for command, expected in [("  HÖGER ", (1, 1)), (" Vänster  ", (1, 0))]:
            with self.subTest(command=command):
                start = (1, 0) if "HÖGER" in command else (1, 1)
                _, state = step(make_game(start), command)

                self.assertEqual(state.position, expected)

    def test_quit_ends_the_game(self):
        outcome, state = step(make_game()," AVSLUTA ")

        self.assertEqual(outcome, Outcome.QUIT)
        self.assertEqual(state.phase, Phase.QUIT)


class QuestionTest(unittest.TestCase):
    def enter_question(self):
        _, state = step(make_game((1, 1)), "ner")
        return state

    def test_entering_question_square_asks_a_question(self):
        outcome, state = step(make_game((1, 1)), "ner")

        self.assertEqual(outcome, Outcome.QUESTION)
        self.assertEqual(state.position, (2, 1))
        self.assertEqual(state.phase, Phase.ANSWER_QUESTION)
        self.assertIn((2, 1), state.discovered)
        self.assertEqual(len(state.current_question["choices"]), 4)

    def test_correct_answer_keeps_the_cat_on_the_square(self):
        state = self.enter_question()

        outcome, state = step(state, correct_answer(state))

        self.assertEqual(outcome, Outcome.CORRECT_ANSWER)
        self.assertEqual(state.position, (2, 1))
        self.assertEqual(state.phase, Phase.MOVE)
        self.assertIsNone(state.current_question)

    def test_wrong_answer_sends_the_cat_back_from_both_directions(self):
        for start, command in [((1, 1), "ner"), ((2, 2), "vänster")]:
            with self.subTest(start=start):
                _, state = step(make_game(start), command)

                outcome, state = step(state, wrong_answer(state))

                self.assertEqual(outcome, Outcome.WRONG_ANSWER)
                self.assertEqual(state.position, start)

    def test_being_sent_back_triggers_nothing_new(self):
        state = self.enter_question()

        _, state = step(state, wrong_answer(state))

        self.assertEqual(state.phase, Phase.MOVE)
        self.assertIsNone(state.current_question)

    def test_invalid_answer_gives_no_penalty(self):
        state = self.enter_question()
        question = state.current_question

        for answer in ["0", "5", "hej", "", "upp"]:
            with self.subTest(answer=answer):
                outcome, state = step(state, answer)

                self.assertEqual(outcome, Outcome.INVALID_ANSWER)
                self.assertEqual(state.position, (2, 1))
                self.assertEqual(state.phase, Phase.ANSWER_QUESTION)
                self.assertEqual(state.current_question, question)

    def test_answer_ignores_surrounding_spaces(self):
        state = self.enter_question()

        outcome, _ = step(state, f" {correct_answer(state)} ")

        self.assertEqual(outcome, Outcome.CORRECT_ANSWER)

    def test_quit_works_during_a_question(self):
        state = self.enter_question()

        outcome, state = step(state, "avsluta")

        self.assertEqual(outcome, Outcome.QUIT)
        self.assertEqual(state.phase, Phase.QUIT)

    def asked_questions(self, state, count):
        asked = []
        for _ in range(count):
            _, state = step(state, "ner")
            asked.append(state.current_question["question"])
            _, state = step(state, wrong_answer(state))
        return asked

    def test_cleared_square_asks_a_new_question_on_the_next_visit(self):
        state = self.enter_question()
        first = state.current_question["question"]

        _, state = step(state, correct_answer(state))
        _, state = step(state, "upp")
        _, state = step(state, "ner")

        self.assertEqual(state.phase, Phase.ANSWER_QUESTION)
        self.assertNotEqual(state.current_question["question"], first)

    def test_questions_do_not_repeat_until_all_are_used(self):
        all_questions = [question["question"] for question in make_questions()]

        asked = self.asked_questions(make_game((1, 1)), len(all_questions) + 1)

        self.assertCountEqual(asked[:-1], all_questions)
        self.assertIn(asked[-1], all_questions)

    def test_choices_are_shuffled_and_controlled_by_the_seed(self):
        def first_choices(seed):
            _, state = step(make_game((1, 1), seed), "ner")
            return state.current_question["choices"]

        orders = {tuple(first_choices(seed)) for seed in range(20)}

        self.assertGreater(len(orders), 1)
        self.assertEqual(first_choices(7), first_choices(7))
        self.assertCountEqual(first_choices(7), make_question()["choices"])

    def test_shuffling_does_not_change_the_loaded_questions(self):
        state = self.enter_question()

        self.assertEqual(state.questions, make_questions())

    def test_cat_can_leave_the_dead_end_through_the_question(self):
        _, state = step(make_game((4, 1)), "vänster")
        _, state = step(state, wrong_answer(state))
        self.assertEqual(state.position, (4, 1))

        _, state = step(state, "vänster")
        _, state = step(state, correct_answer(state))
        outcome, state = step(state, "upp")

        self.assertEqual(outcome, Outcome.MOVED)
        self.assertEqual(state.position, (3, 0))


class FetchTest(unittest.TestCase):
    def test_entering_fetch_without_cake_offers_all_cakes(self):
        outcome, state = step(make_game((0, 3)), "höger")

        self.assertEqual(outcome, Outcome.CAKE_CHOICE)
        self.assertEqual(state.phase, Phase.CHOOSE_CAKE)
        self.assertEqual(state.cake_choices, CAKES)

    def test_entering_fetch_with_cake_offers_the_other_four(self):
        state = enter_fetch(["kanelbulle"])

        self.assertEqual(len(state.cake_choices), 4)
        self.assertNotIn("kanelbulle", state.cake_choices)

    def test_choosing_a_cake_fills_the_inventory(self):
        state = enter_fetch()

        outcome, state = choose_cake(state, "morotskaka")

        self.assertEqual(outcome, Outcome.CAKE_CHOSEN)
        self.assertEqual(state.inventory, ["morotskaka"])
        self.assertEqual(state.position, FETCH_POSITION)
        self.assertEqual(state.phase, Phase.MOVE)

    def test_choosing_a_new_cake_returns_the_old_one(self):
        state = enter_fetch(["kanelbulle"])

        _, state = choose_cake(state, "chokladboll")

        self.assertEqual(state.inventory, ["chokladboll"])

    def test_invalid_choice_asks_again(self):
        state = enter_fetch()

        for choice in ["0", "6", "hej", "", "upp"]:
            with self.subTest(choice=choice):
                outcome, state = step(state, choice)

                self.assertEqual(outcome, Outcome.INVALID_CAKE_CHOICE)
                self.assertEqual(state.phase, Phase.CHOOSE_CAKE)
                self.assertEqual(state.inventory, [])

    def test_cat_with_favorite_cake_must_swap_and_can_fetch_it_again(self):
        state = enter_fetch([FAVORITE_CAKE])
        self.assertNotIn(FAVORITE_CAKE, state.cake_choices)

        _, state = choose_cake(state, "kanelbulle")
        _, state = step(state, "vänster")
        _, state = step(state, "höger")
        _, state = choose_cake(state, FAVORITE_CAKE)

        self.assertEqual(state.inventory, [FAVORITE_CAKE])

    def test_quit_works_during_a_cake_choice(self):
        outcome, state = step(enter_fetch(), "avsluta")

        self.assertEqual(outcome, Outcome.QUIT)
        self.assertEqual(state.phase, Phase.QUIT)


class WitchTest(unittest.TestCase):
    def test_favorite_cake_opens_the_way(self):
        outcome, state = enter_leave([FAVORITE_CAKE])

        self.assertEqual(outcome, Outcome.WITCH_CORRECT)
        self.assertEqual(state.position, LEAVE_POSITION)
        self.assertEqual(state.inventory, [])
        self.assertTrue(state.witch_has_cake)

    def test_wrong_cake_sends_the_cat_to_start_with_the_cake(self):
        outcome, state = enter_leave(["kanelbulle"])

        self.assertEqual(outcome, Outcome.WITCH_WRONG)
        self.assertEqual(state.position, START_POSITION)
        self.assertEqual(state.inventory, ["kanelbulle"])
        self.assertFalse(state.witch_has_cake)

    def test_no_cake_sends_the_cat_to_start(self):
        outcome, state = enter_leave()

        self.assertEqual(outcome, Outcome.WITCH_NO_CAKE)
        self.assertEqual(state.position, START_POSITION)

    def test_leave_works_as_free_after_the_witch_has_her_cake(self):
        _, state = enter_leave([FAVORITE_CAKE])
        _, state = step(state, "upp")

        outcome, state = step(state, "ner")

        self.assertEqual(outcome, Outcome.MOVED)
        self.assertEqual(state.position, LEAVE_POSITION)


class HomeTest(unittest.TestCase):
    def test_home_wins_the_game(self):
        _, state = enter_leave([FAVORITE_CAKE])

        outcome, state = step(state, "höger")

        self.assertEqual(outcome, Outcome.HOME)
        self.assertEqual(state.position, HOME_POSITION)
        self.assertEqual(state.phase, Phase.WON)

    def test_home_can_only_be_reached_through_leave(self):
        seen = {START_POSITION}
        to_visit = [START_POSITION]
        while to_visit:
            row, col = to_visit.pop()
            for next_row, next_col in [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]:
                position = (next_row, next_col)
                on_map = 0 <= next_row < len(GRID) and 0 <= next_col < len(GRID)
                if on_map and position not in seen and position != LEAVE_POSITION and GRID[next_row][next_col] != "blocked":
                    seen.add(position)
                    to_visit.append(position)

        self.assertNotIn(HOME_POSITION, seen)

    def test_whole_way_home_can_be_played_without_a_terminal(self):
        state = make_game()
        for command in ["höger", "höger", "höger", "höger"]:
            _, state = step(state, command)
        self.assertEqual(state.position, FETCH_POSITION)

        _, state = choose_cake(state, FAVORITE_CAKE)
        for command in ["vänster", "vänster", "vänster", "ner", "ner"]:
            _, state = step(state, command)
        self.assertEqual(state.position, (2, 1))

        _, state = step(state, correct_answer(state))
        for command in ["höger", "höger", "ner"]:
            outcome, state = step(state, command)
        self.assertEqual(outcome, Outcome.WITCH_CORRECT)

        outcome, state = step(state, "höger")
        self.assertEqual(outcome, Outcome.HOME)
        self.assertEqual(state.phase, Phase.WON)


if __name__ == "__main__":
    unittest.main()
