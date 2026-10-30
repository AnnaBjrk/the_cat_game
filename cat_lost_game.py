"""Cat Lost: hjälp en bortrollad katt hem över en spelplan med 5x5 rutor."""

import json
import random
import textwrap
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import zip_longest
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTIONS_PATH = BASE_DIR / "cat_lost_questions.json"
STORY_PATH = BASE_DIR / "cat_lost_story.json"

GRID = [
    ["start",    "free",     "free",    "free",    "fetch"],
    ["free",     "free",     "blocked", "blocked", "blocked"],
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
YES_ANSWER = "ja"
NO_ANSWER = "nej"

SQUARE_SYMBOLS = {
    "start": "S",
    "free": "·",
    "blocked": "■",
    "question": "F",
    "fetch": "C",
    "leave": "X",
    "home": "H",
}
SQUARE_NAMES = {
    "start": "start",
    "free": "fri väg",
    "blocked": "hus",
    "question": "fråga",
    "fetch": "café",
    "leave": "häxa",
    "home": "hem",
}
CAT_SYMBOL = "K"
UNKNOWN_SYMBOL = "?"
GAME_TITLE = "CAT LOST"
LEGEND_ROWS = 5
LEGEND_COLUMN_WIDTH = 13
MESSAGE_WIDTH = 72

COMMANDS_TEXT = "Kommandon: upp, ner, vänster, höger, avsluta."
INVALID_COMMAND_TEXT = f"Det kommandot finns inte.\n{COMMANDS_TEXT}"
INVALID_CHOICE_TEXT = "Svara med en av siffrorna:"
INVALID_WITCH_ANSWER_TEXT = "Svara ja eller nej."
CAKE_CHOSEN_TEXT = "Du tar med dig en {cake}."
QUIT_TEXT = "Hej då! Katten väntar på att du ska komma tillbaka."

ANSI_YELLOW = "\033[33m"
ANSI_ORANGE = "\033[38;5;208m"
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_ITALIC = "\033[3m"
ANSI_REVERSE = "\033[7m"
CLEAR_SCREEN = "\033[2J\033[H"
CAT_FRAMES = [
    (ANSI_YELLOW, "\n".join([
        r"  /\_/\     ",
        r" ( ^.^ )/   ",
        r"  /   \     ",
        r" _|   |_    ",
    ])),
    (ANSI_ORANGE, "\n".join([
        r"     /\_/\  ",
        r"   \( ^.^ ) ",
        r"     /   \  ",
        r"    _|   |_ ",
    ])),
]
FRAME_HEIGHT = 4
ANIMATION_FRAMES = 10
FRAME_SECONDS = 0.3

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
    OFFER_CAKE = auto()
    WON = auto()
    QUIT = auto()


class Outcome(Enum):
    MOVED = auto()
    BLOCKED = auto()
    OFF_MAP = auto()
    INVALID_COMMAND = auto()
    QUESTION = auto()
    CORRECT_ANSWER = auto()
    WRONG_ANSWER = auto()
    INVALID_ANSWER = auto()
    CAKE_CHOICE = auto()
    CAKE_CHOSEN = auto()
    INVALID_CAKE_CHOICE = auto()
    WITCH_OFFER = auto()
    INVALID_WITCH_ANSWER = auto()
    WITCH_DECLINED = auto()
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
    if not state.inventory:
        state.position = START_POSITION
        return Outcome.WITCH_NO_CAKE

    state.phase = Phase.OFFER_CAKE
    return Outcome.WITCH_OFFER


def answer_witch(state, answer):
    if answer not in (YES_ANSWER, NO_ANSWER):
        return Outcome.INVALID_WITCH_ANSWER

    state.phase = Phase.MOVE
    if answer == NO_ANSWER:
        state.position = state.previous_position
        return Outcome.WITCH_DECLINED
    if FAVORITE_CAKE in state.inventory:
        state.inventory = []
        state.witch_has_cake = True
        return Outcome.WITCH_CORRECT

    state.position = START_POSITION
    return Outcome.WITCH_WRONG


def move(state, direction):
    row = state.position[0] + direction[0]
    col = state.position[1] + direction[1]
    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        return Outcome.OFF_MAP

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
    if state.phase == Phase.OFFER_CAKE:
        return answer_witch(state, command), state
    if command not in DIRECTIONS:
        return Outcome.INVALID_COMMAND, state
    return move(state, DIRECTIONS[command]), state


def numbered(options):
    return "\n".join(f"{number}. {option}" for number, option in enumerate(options, start=1))


def question_text(question):
    return f"{question['question']}\n{numbered(question['choices'])}"


def witch_offer_text(state, story):
    return story["witch_offer"].format(cake=state.inventory[0])


def start_message(story):
    return f"{story['start_story']}\n\n{COMMANDS_TEXT}"


def message_for(outcome, state, story):
    match outcome:
        case Outcome.MOVED:
            return state.rng.choice(story["free_descriptions"])
        case Outcome.BLOCKED:
            return story["blocked"]
        case Outcome.OFF_MAP:
            return story["off_map"]
        case Outcome.INVALID_COMMAND:
            return INVALID_COMMAND_TEXT
        case Outcome.QUESTION:
            return f"{story['question_intro']}\n\n{question_text(state.current_question)}"
        case Outcome.CORRECT_ANSWER:
            return story["question_correct"]
        case Outcome.WRONG_ANSWER:
            return story["question_wrong"]
        case Outcome.INVALID_ANSWER:
            return f"{INVALID_CHOICE_TEXT}\n{numbered(state.current_question['choices'])}"
        case Outcome.CAKE_CHOICE:
            return f"{story['fetch']}\n\n{numbered(state.cake_choices)}"
        case Outcome.CAKE_CHOSEN:
            return CAKE_CHOSEN_TEXT.format(cake=state.inventory[0])
        case Outcome.INVALID_CAKE_CHOICE:
            return f"{INVALID_CHOICE_TEXT}\n{numbered(state.cake_choices)}"
        case Outcome.WITCH_OFFER:
            return f"{story['leave']}\n\n{witch_offer_text(state, story)}"
        case Outcome.INVALID_WITCH_ANSWER:
            return f"{INVALID_WITCH_ANSWER_TEXT}\n{witch_offer_text(state, story)}"
        case Outcome.WITCH_DECLINED:
            return story["witch_declined"]
        case Outcome.WITCH_CORRECT:
            return story["witch_correct"]
        case Outcome.WITCH_WRONG:
            return story["witch_wrong"]
        case Outcome.WITCH_NO_CAKE:
            return f"{story['leave']}\n\n{story['witch_no_cake']}"
        case Outcome.HOME:
            return story["home"]
        case Outcome.QUIT:
            return QUIT_TEXT


def styled(style, text):
    return f"{style}{text}{ANSI_RESET}"


def format_line(line):
    if not line:
        return line
    return styled(ANSI_ITALIC if line == COMMANDS_TEXT else ANSI_BOLD, line)


def format_message(message):
    lines = []
    for paragraph in message.split("\n"):
        lines.extend(textwrap.wrap(paragraph, MESSAGE_WIDTH) or [""])
    return "\n".join(format_line(line) for line in lines)


def square_cell(state, position):
    if position == state.position:
        return styled(ANSI_BOLD + ANSI_REVERSE, f" {CAT_SYMBOL} ")
    if position in state.discovered:
        row, col = position
        return f" {SQUARE_SYMBOLS[GRID[row][col]]} "
    return styled(ANSI_DIM, f" {UNKNOWN_SYMBOL} ")


def grid_border(left, middle, right):
    return left + middle.join(["───"] * GRID_SIZE) + right


def grid_lines(state):
    lines = [grid_border("┌", "┬", "┐")]
    for row in range(GRID_SIZE):
        if row > 0:
            lines.append(grid_border("├", "┼", "┤"))
        cells = [square_cell(state, (row, col)) for col in range(GRID_SIZE)]
        lines.append("│" + "│".join(cells) + "│")
    lines.append(grid_border("└", "┴", "┘"))
    return lines


def legend_lines(state):
    discovered_squares = {GRID[row][col] for row, col in state.discovered}
    entries = [
        f"{CAT_SYMBOL} katten",
        f"{UNKNOWN_SYMBOL} okänd",
        *(
            f"{SQUARE_SYMBOLS[square]} {name}"
            for square, name in SQUARE_NAMES.items()
            if square in discovered_squares
        ),
    ]
    return [
        f"{left:<{LEGEND_COLUMN_WIDTH}}{right}".rstrip()
        for left, right in zip_longest(
            entries[:LEGEND_ROWS], entries[LEGEND_ROWS:], fillvalue=""
        )
    ]


def side_panel(state, round_number):
    cake = state.inventory[0] if state.inventory else "ingen"
    return [
        "",
        styled(ANSI_BOLD, GAME_TITLE),
        "",
        f"Runda {round_number}",
        f"Kaka: {cake}",
        "",
        *legend_lines(state),
    ]


def render_map(state, round_number):
    return "\n".join(
        f"{grid_line}   {panel_line}".rstrip()
        for grid_line, panel_line in zip_longest(
            grid_lines(state), side_panel(state, round_number), fillvalue=""
        )
    )


def play_win_animation():
    for number in range(ANIMATION_FRAMES):
        if number > 0:
            print(f"\033[{FRAME_HEIGHT}A", end="")
        color, frame = CAT_FRAMES[number % len(CAT_FRAMES)]
        print(f"{color}{frame}{ANSI_RESET}", flush=True)
        time.sleep(FRAME_SECONDS)


PROMPTS = {
    Phase.MOVE: "Vart vill du gå? (upp/ner/vänster/höger/avsluta): ",
    Phase.ANSWER_QUESTION: "Ditt svar: ",
    Phase.CHOOSE_CAKE: "Din kaka: ",
    Phase.OFFER_CAKE: "Ditt svar: ",
}


def main():
    content = load_content()
    state = new_game(content.questions, random.Random())
    message = start_message(content.story)
    round_number = 1

    while state.phase not in (Phase.WON, Phase.QUIT):
        print(f"{CLEAR_SCREEN}{render_map(state, round_number)}")
        print(f"\n{format_message(message)}")
        outcome, state = step(state, input(styled(ANSI_BOLD, PROMPTS[state.phase])))
        if outcome == Outcome.HOME:
            print(CLEAR_SCREEN, end="")
            play_win_animation()
        message = message_for(outcome, state, content.story)
        round_number += 1

    print(f"\n{format_message(message)}")


if __name__ == "__main__":
    main()
