import contextlib
import io
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cat_lost_game import (
    ANIMATION_FRAMES,
    ANSI_RESET,
    CAKES,
    CAT_FRAMES,
    FRAME_SECONDS,
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
    main,
    message_for,
    new_game,
    play_win_animation,
    render_map,
    start_message,
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
    "witch_offer",
    "witch_declined",
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


def give_cake_to_witch(inventory):
    _, state = enter_leave(inventory)
    return step(state, "ja")


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
        for position, command in [((4, 1), "ner"), ((0, 4), "höger")]:
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
    def test_witch_asks_about_any_cake(self):
        for cake in [FAVORITE_CAKE, "kanelbulle"]:
            with self.subTest(cake=cake):
                outcome, state = enter_leave([cake])

                self.assertEqual(outcome, Outcome.WITCH_OFFER)
                self.assertEqual(state.phase, Phase.OFFER_CAKE)
                self.assertEqual(state.position, LEAVE_POSITION)
                self.assertEqual(state.inventory, [cake])

    def test_answering_no_sends_the_cat_back_with_the_cake(self):
        _, state = enter_leave([FAVORITE_CAKE])

        outcome, state = step(state, " NEJ ")

        self.assertEqual(outcome, Outcome.WITCH_DECLINED)
        self.assertEqual(state.position, (2, 3))
        self.assertEqual(state.inventory, [FAVORITE_CAKE])
        self.assertEqual(state.phase, Phase.MOVE)
        self.assertFalse(state.witch_has_cake)

    def test_witch_asks_again_after_answering_no(self):
        _, state = enter_leave([FAVORITE_CAKE])
        _, state = step(state, "nej")

        outcome, state = step(state, "ner")

        self.assertEqual(outcome, Outcome.WITCH_OFFER)

    def test_invalid_answer_asks_again(self):
        _, state = enter_leave([FAVORITE_CAKE])

        for answer in ["1", "kanske", "", "höger"]:
            with self.subTest(answer=answer):
                outcome, state = step(state, answer)

                self.assertEqual(outcome, Outcome.INVALID_WITCH_ANSWER)
                self.assertEqual(state.phase, Phase.OFFER_CAKE)
                self.assertEqual(state.inventory, [FAVORITE_CAKE])

    def test_quit_works_during_the_witch_question(self):
        _, state = enter_leave([FAVORITE_CAKE])

        outcome, state = step(state, "avsluta")

        self.assertEqual(outcome, Outcome.QUIT)
        self.assertEqual(state.phase, Phase.QUIT)

    def test_favorite_cake_opens_the_way(self):
        outcome, state = give_cake_to_witch([FAVORITE_CAKE])

        self.assertEqual(outcome, Outcome.WITCH_CORRECT)
        self.assertEqual(state.position, LEAVE_POSITION)
        self.assertEqual(state.inventory, [])
        self.assertEqual(state.phase, Phase.MOVE)
        self.assertTrue(state.witch_has_cake)

    def test_wrong_cake_sends_the_cat_to_start_with_the_cake(self):
        outcome, state = give_cake_to_witch(["kanelbulle"])

        self.assertEqual(outcome, Outcome.WITCH_WRONG)
        self.assertEqual(state.phase, Phase.MOVE)
        self.assertEqual(state.position, START_POSITION)
        self.assertEqual(state.inventory, ["kanelbulle"])
        self.assertFalse(state.witch_has_cake)

    def test_no_cake_sends_the_cat_to_start(self):
        outcome, state = enter_leave()

        self.assertEqual(outcome, Outcome.WITCH_NO_CAKE)
        self.assertEqual(state.position, START_POSITION)

    def test_leave_works_as_free_after_the_witch_has_her_cake(self):
        _, state = give_cake_to_witch([FAVORITE_CAKE])
        _, state = step(state, "upp")

        outcome, state = step(state, "ner")

        self.assertEqual(outcome, Outcome.MOVED)
        self.assertEqual(state.position, LEAVE_POSITION)


class HomeTest(unittest.TestCase):
    def test_home_wins_the_game(self):
        _, state = give_cake_to_witch([FAVORITE_CAKE])

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
        self.assertEqual(outcome, Outcome.WITCH_OFFER)

        outcome, state = step(state, "ja")
        self.assertEqual(outcome, Outcome.WITCH_CORRECT)

        outcome, state = step(state, "höger")
        self.assertEqual(outcome, Outcome.HOME)
        self.assertEqual(state.phase, Phase.WON)


def make_marked_story():
    story = {key: f"<{key}>" for key in STORY_KEYS}
    story["free_descriptions"] = ["<free 1>", "<free 2>"]
    return story


class MessageTest(unittest.TestCase):
    def message_after(self, state, command):
        outcome, state = step(state, command)
        return message_for(outcome, state, make_marked_story())

    def test_start_message_has_story_and_commands(self):
        message = start_message(make_marked_story())

        self.assertIn("<start_story>", message)
        for command in ["upp", "ner", "vänster", "höger", "avsluta"]:
            self.assertIn(command, message)

    def test_blocked_and_edge_give_the_blocked_text(self):
        self.assertEqual(self.message_after(make_game((1, 1)), "höger"), "<blocked>")
        self.assertEqual(self.message_after(make_game(), "upp"), "<blocked>")

    def test_free_square_gives_a_free_description(self):
        message = self.message_after(make_game(), "höger")

        self.assertIn(message, make_marked_story()["free_descriptions"])

    def test_returning_to_start_gives_a_free_description_and_not_the_story(self):
        message = self.message_after(make_game((0, 1)), "vänster")

        self.assertIn(message, make_marked_story()["free_descriptions"])

    def test_opened_leave_gives_a_free_description(self):
        _, state = give_cake_to_witch([FAVORITE_CAKE])
        _, state = step(state, "upp")

        message = self.message_after(state, "ner")

        self.assertIn(message, make_marked_story()["free_descriptions"])

    def test_question_shows_intro_question_and_numbered_choices(self):
        outcome, state = step(make_game((1, 1)), "ner")

        message = message_for(outcome, state, make_marked_story())

        self.assertIn("<question_intro>", message)
        self.assertIn(state.current_question["question"], message)
        for number, choice in enumerate(state.current_question["choices"], start=1):
            self.assertIn(f"{number}. {choice}", message)

    def test_answers_give_the_right_text(self):
        _, state = step(make_game((1, 1)), "ner")
        self.assertEqual(self.message_after(state, correct_answer(state)), "<question_correct>")

        _, state = step(make_game((1, 1)), "ner")
        self.assertEqual(self.message_after(state, wrong_answer(state)), "<question_wrong>")

    def test_invalid_answer_repeats_the_choices(self):
        _, state = step(make_game((1, 1)), "ner")

        message = self.message_after(state, "hej")

        self.assertIn(f"1. {state.current_question['choices'][0]}", message)
        self.assertNotIn("<question_intro>", message)

    def test_fetch_shows_text_and_numbered_cakes(self):
        message = self.message_after(make_game((0, 3)), "höger")

        self.assertIn("<fetch>", message)
        for number, cake in enumerate(CAKES, start=1):
            self.assertIn(f"{number}. {cake}", message)

    def test_invalid_cake_choice_repeats_the_cakes(self):
        message = self.message_after(enter_fetch(), "hej")

        self.assertIn(f"1. {CAKES[0]}", message)
        self.assertNotIn("<fetch>", message)

    def test_chosen_cake_is_named(self):
        state = enter_fetch()

        message = self.message_after(state, str(CAKES.index("morotskaka") + 1))

        self.assertIn("morotskaka", message)

    def test_witch_gives_leave_text_followed_by_the_offer_or_no_cake_text(self):
        for inventory, expected in [
            (["kanelbulle"], "<witch_offer>"),
            ([], "<witch_no_cake>"),
        ]:
            with self.subTest(inventory=inventory):
                outcome, state = enter_leave(inventory)

                message = message_for(outcome, state, make_marked_story())

                self.assertLess(message.index("<leave>"), message.index(expected))

    def test_witch_offer_names_the_cake_in_the_real_story(self):
        outcome, state = enter_leave(["kanelbulle"])

        message = message_for(outcome, state, load_content().story)

        self.assertIn("kanelbulle", message)

    def test_answers_to_the_witch_give_the_right_text(self):
        for inventory, answer, expected in [
            ([FAVORITE_CAKE], "ja", "<witch_correct>"),
            (["kanelbulle"], "ja", "<witch_wrong>"),
            ([FAVORITE_CAKE], "nej", "<witch_declined>"),
        ]:
            with self.subTest(inventory=inventory, answer=answer):
                _, state = enter_leave(inventory)

                self.assertEqual(self.message_after(state, answer), expected)

    def test_invalid_witch_answer_repeats_the_offer(self):
        _, state = enter_leave(["kanelbulle"])

        message = self.message_after(state, "kanske")

        self.assertIn("<witch_offer>", message)
        self.assertNotIn("<leave>", message)

    def test_home_gives_the_home_text(self):
        _, state = give_cake_to_witch([FAVORITE_CAKE])

        self.assertEqual(self.message_after(state, "höger"), "<home>")

    def test_invalid_command_and_quit_give_a_message(self):
        self.assertTrue(self.message_after(make_game(), "hoppa"))
        self.assertTrue(self.message_after(make_game(), "avsluta"))

    def test_every_outcome_has_a_message_with_the_real_story(self):
        story = load_content().story
        for outcome in Outcome:
            with self.subTest(outcome=outcome):
                state = make_game()
                state.current_question = make_question()
                state.cake_choices = CAKES
                state.inventory = ["kanelbulle"]

                self.assertTrue(message_for(outcome, state, story))


class RenderMapTest(unittest.TestCase):
    def test_new_game_shows_only_the_cat(self):
        expected = "\n".join(
            ["[katt ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]"]
            + ["[  ?  ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]"] * 4
            + ["Kaka: ingen"]
        )

        self.assertEqual(render_map(make_game()), expected)

    def test_visited_square_shows_its_swedish_name(self):
        _, state = step(make_game(), "höger")

        self.assertEqual(
            render_map(state).splitlines()[0],
            "[start] [katt ] [  ?  ] [  ?  ] [  ?  ]",
        )

    def test_blocked_square_shows_after_an_attempt(self):
        _, state = step(make_game((1, 1)), "höger")

        self.assertIn("[ hus ]", render_map(state).splitlines()[1])

    def test_all_square_types_have_swedish_names_and_the_same_width(self):
        state = make_game()
        state.discovered = {
            (row, col) for row in range(len(GRID)) for col in range(len(GRID))
        }

        lines = render_map(state).splitlines()[:len(GRID)]

        for name in ["fri", "hus", "fråga", "café", "häxa", "hem"]:
            self.assertIn(name, "\n".join(lines))
        for line in lines:
            self.assertEqual(len(line), 39)

    def test_inventory_is_shown(self):
        state = make_game()
        state.inventory = ["äppelpaj"]

        self.assertIn("Kaka: äppelpaj", render_map(state))


class TerminalTest(unittest.TestCase):
    def test_game_starts_and_can_be_quit(self):
        game_file = Path(__file__).with_name("cat_lost_game.py")

        result = subprocess.run(
            [sys.executable, str(game_file)],
            input="avsluta\n",
            capture_output=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(load_content().story["start_story"], result.stdout)
        self.assertIn("Kaka: ingen", result.stdout)

    def test_whole_game_runs_through_the_terminal_loop(self):
        moves = iter(["höger"] * 4 + ["vänster"] * 3 + ["ner"] * 2 + ["höger", "höger", "ner", "höger"])
        games = []

        def start_game(questions, rng):
            games.append(new_game(questions, rng))
            return games[0]

        def read_input(prompt):
            state = games[0]
            if state.phase == Phase.ANSWER_QUESTION:
                return correct_answer(state)
            if state.phase == Phase.CHOOSE_CAKE:
                return str(state.cake_choices.index(FAVORITE_CAKE) + 1)
            if state.phase == Phase.OFFER_CAKE:
                return "ja"
            return next(moves)

        output = io.StringIO()
        with (
            mock.patch("cat_lost_game.new_game", start_game),
            mock.patch("builtins.input", read_input),
            mock.patch("cat_lost_game.play_win_animation", lambda: print("<dans>")),
            contextlib.redirect_stdout(output),
        ):
            main()

        story = load_content().story
        self.assertEqual(games[0].phase, Phase.WON)
        self.assertLess(output.getvalue().index("<dans>"), output.getvalue().index(story["home"]))


class WinAnimationTest(unittest.TestCase):
    def play(self):
        output = io.StringIO()
        with mock.patch("time.sleep") as sleep, contextlib.redirect_stdout(output):
            play_win_animation()
        return output.getvalue(), sleep

    def test_animation_lasts_about_three_seconds(self):
        self.assertAlmostEqual(ANIMATION_FRAMES * FRAME_SECONDS, 3, delta=0.5)

        _, sleep = self.play()

        self.assertEqual(sleep.call_count, ANIMATION_FRAMES)

    def test_animation_has_at_least_two_alternating_frames(self):
        output, _ = self.play()

        self.assertGreaterEqual(len(CAT_FRAMES), 2)
        for _, frame in CAT_FRAMES:
            self.assertIn(frame, output)

    def test_colors_are_reset_at_the_end(self):
        output, _ = self.play()

        self.assertTrue(output.rstrip().endswith(ANSI_RESET))

    def test_frames_fit_the_terminal_and_overwrite_each_other(self):
        for _, frame in CAT_FRAMES:
            lines = frame.split("\n")
            self.assertEqual(len(lines), len(CAT_FRAMES[0][1].split("\n")))
            for line in lines:
                self.assertLessEqual(len(line), 80)
                self.assertEqual(len(line), len(lines[0]))


if __name__ == "__main__":
    unittest.main()
