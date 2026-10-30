"""Cat Lost: hjälp en bortrollad katt hem över en spelplan med 5x5 rutor."""

import json
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTIONS_PATH = BASE_DIR / "cat_lost_questions.json"
STORY_PATH = BASE_DIR / "cat_lost_story.json"

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


class ContentError(Exception):
    """En innehållsfil saknas eller uppfyller inte kraven."""


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


def validate_story(story):
    missing = [key for key in STORY_KEYS if key not in story]
    if missing:
        raise ContentError(f"Texter saknas i berättelsen: {', '.join(missing)}")


def load_content(questions_path=QUESTIONS_PATH, story_path=STORY_PATH):
    questions = read_json(questions_path)
    story = read_json(story_path)
    validate_story(story)
    return Content(questions, story)
