"""Cat Lost: hjälp en bortrollad katt hem över en spelplan med 5x5 rutor."""

import json
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTIONS_PATH = BASE_DIR / "cat_lost_questions.json"
STORY_PATH = BASE_DIR / "cat_lost_story.json"


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
