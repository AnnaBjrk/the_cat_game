"""Cat Lost: hjälp en bortrollad katt hem över en spelplan med 5x5 rutor."""

import json
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTIONS_PATH = BASE_DIR / "cat_lost_questions.json"
STORY_PATH = BASE_DIR / "cat_lost_story.json"

GRID = [
    ["start",    "free",     "free",    "free",    "fetch"],
    ["free",     "free",     "blocked", "blocked", "free"],
    ["free",     "question", "free",    "free",    "blocked"],
    ["free",     "blocked",  "blocked", "leave",   "home"],
    ["question", "free",     "free",    "blocked", "blocked"],
]
GRID_SIZE = len(GRID)
START_POSITION = (0, 0)
FETCH_POSITION = (0, 4)
LEAVE_POSITION = (3, 3)
HOME_POSITION = (3, 4)
BLOCKED_SQUARE = "blocked"
QUESTION_SQUARE = "question"

CAKES = ["kanelbulle", "chokladboll", "prinsesstårta", "morotskaka", "äppelpaj"]
FAVORITE_CAKE = "äppelpaj"

QUIT_COMMAND = "avsluta"
DIRECTIONS = {
    "upp": (-1, 0),
    "ner": (1, 0),
    "vänster": (0, -1),
    "höger": (0, 1),
}


class Phase(Enum):
    MOVE = auto()
    ANSWER_QUESTION = auto()
    CHOOSE_CAKE = auto()
    WON = auto()
    QUIT = auto()


class Outcome(Enum):
    MOVED = auto()
    BLOCKED = auto()
    INVALID_COMMAND = auto()
    QUESTION = auto()
    CORRECT_ANSWER = auto()
    WRONG_ANSWER = auto()
    INVALID_ANSWER = auto()
    CAKE_CHOICE = auto()
    CAKE_CHOSEN = auto()
    INVALID_CAKE_CHOICE = auto()
    WITCH_CORRECT = auto()
    WITCH_WRONG = auto()
    WITCH_NO_CAKE = auto()
    HOME = auto()
    QUIT = auto()


class ContentError(Exception):
    """En innehållsfil saknas eller innehåller ogiltig JSON."""


@dataclass(frozen=True)
class Content:
    questions: list[dict]
    story: dict


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ContentError(f"Filen saknas: {path}") from None
    except json.JSONDecodeError as error:
        raise ContentError(f"Ogiltig JSON i {path}: {error}") from None


def load_content(questions_path=QUESTIONS_PATH, story_path=STORY_PATH):
    return Content(read_json(questions_path), read_json(story_path))


@dataclass
class GameState:
    questions: list[dict]
    rng: random.Random
    position: tuple[int, int] = START_POSITION
    previous_position: tuple[int, int] = START_POSITION
    discovered: set[tuple[int, int]] = field(default_factory=lambda: {START_POSITION})
    phase: Phase = Phase.MOVE
    question_queue: list[dict] = field(default_factory=list)
    current_question: dict | None = None
    inventory: list[str] = field(default_factory=list)
    cake_choices: list[str] = field(default_factory=list)
    witch_has_cake: bool = False


def new_game(questions, rng):
    return GameState(questions, rng)


def ask_question(state):
    if not state.question_queue:
        state.question_queue = state.rng.sample(state.questions, len(state.questions))
    question = state.question_queue.pop()
    choices = state.rng.sample(question["choices"], len(question["choices"]))
    state.current_question = {**question, "choices": choices}
    state.phase = Phase.ANSWER_QUESTION
    return Outcome.QUESTION


def chosen_option(options, player_input):
    numbers = [str(number) for number in range(1, len(options) + 1)]
    if player_input in numbers:
        return options[int(player_input) - 1]
    return None


def answer_question(state, answer):
    choice = chosen_option(state.current_question["choices"], answer)
    if choice is None:
        return Outcome.INVALID_ANSWER

    is_correct = choice == state.current_question["answer"]
    state.current_question = None
    state.phase = Phase.MOVE
    if is_correct:
        return Outcome.CORRECT_ANSWER

    state.position = state.previous_position
    return Outcome.WRONG_ANSWER


def offer_cakes(state):
    state.cake_choices = [cake for cake in CAKES if cake not in state.inventory]
    state.phase = Phase.CHOOSE_CAKE
    return Outcome.CAKE_CHOICE


def choose_cake(state, player_input):
    cake = chosen_option(state.cake_choices, player_input)
    if cake is None:
        return Outcome.INVALID_CAKE_CHOICE

    state.inventory = [cake]
    state.phase = Phase.MOVE
    return Outcome.CAKE_CHOSEN


def meet_witch(state):
    if state.witch_has_cake:
        return Outcome.MOVED
    if FAVORITE_CAKE in state.inventory:
        state.inventory = []
        state.witch_has_cake = True
        return Outcome.WITCH_CORRECT

    outcome = Outcome.WITCH_WRONG if state.inventory else Outcome.WITCH_NO_CAKE
    state.position = START_POSITION
    return outcome


def move(state, direction):
    row = state.position[0] + direction[0]
    col = state.position[1] + direction[1]
    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        return Outcome.BLOCKED

    state.discovered.add((row, col))
    if GRID[row][col] == BLOCKED_SQUARE:
        return Outcome.BLOCKED

    state.previous_position = state.position
    state.position = (row, col)
    if GRID[row][col] == QUESTION_SQUARE:
        return ask_question(state)
    if state.position == FETCH_POSITION:
        return offer_cakes(state)
    if state.position == LEAVE_POSITION:
        return meet_witch(state)
    if state.position == HOME_POSITION:
        state.phase = Phase.WON
        return Outcome.HOME
    return Outcome.MOVED


def step(state, player_input):
    command = player_input.strip().lower()
    if command == QUIT_COMMAND:
        state.phase = Phase.QUIT
        return Outcome.QUIT, state
    if state.phase == Phase.ANSWER_QUESTION:
        return answer_question(state, command), state
    if state.phase == Phase.CHOOSE_CAKE:
        return choose_cake(state, command), state
    if command not in DIRECTIONS:
        return Outcome.INVALID_COMMAND, state
    return move(state, DIRECTIONS[command]), state
