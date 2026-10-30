"""Cat Lost: hjälp en bortrollad katt hem över en spelplan med 5x5 rutor."""

import json
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
BLOCKED_SQUARE = "blocked"

QUIT_COMMAND = "avsluta"
DIRECTIONS = {
    "upp": (-1, 0),
    "ner": (1, 0),
    "vänster": (0, -1),
    "höger": (0, 1),
}


class Phase(Enum):
    MOVE = auto()
    QUIT = auto()


class Outcome(Enum):
    MOVED = auto()
    BLOCKED = auto()
    INVALID_COMMAND = auto()
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
    position: tuple[int, int] = START_POSITION
    discovered: set[tuple[int, int]] = field(default_factory=lambda: {START_POSITION})
    phase: Phase = Phase.MOVE


def new_game():
    return GameState()


def move(state, direction):
    row = state.position[0] + direction[0]
    col = state.position[1] + direction[1]
    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        return Outcome.BLOCKED

    state.discovered.add((row, col))
    if GRID[row][col] == BLOCKED_SQUARE:
        return Outcome.BLOCKED

    state.position = (row, col)
    return Outcome.MOVED


def step(state, player_input):
    command = player_input.strip().lower()
    if command == QUIT_COMMAND:
        state.phase = Phase.QUIT
        return Outcome.QUIT, state
    if command not in DIRECTIONS:
        return Outcome.INVALID_COMMAND, state
    return move(state, DIRECTIONS[command]), state
