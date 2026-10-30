"""
Cat Goes Home — a node/edge based riddle game.

This file is self-contained and runnable as-is: it parses each obstacle's
SKILL.md (for tone/instructions metadata) and its references/riddles.txt
(for the actual questions), then runs the game as a graph of nodes
connected by edges, exactly like the ADK Workflow design we sketched.

Where this would plug into real google.adk:
  - Each `ObstacleNode.ask()` call is where an LlmAgent would normally run,
    using the SKILL.md content as its instructions and picking/phrasing
    the riddle itself (with more natural language, hints, etc).
  - `SkillToolset(skills_dir="skills/")` is the real ADK class that would
    load these SKILL.md files on demand (progressive disclosure) instead
    of us parsing them manually below.
  - The edges dict at the bottom of this file maps 1:1 onto the
    `edges=[...]` list in a real `google.adk.workflow.Workflow`.
"""

import os
import asyncio
import random
import re
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv
from opentelemetry import trace
from phoenix.otel import register
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

load_dotenv()

PHOENIX_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
VICTORY_MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.5-flash-lite")

tracer_provider = register(
    project_name="cat-goes-home",
    endpoint=PHOENIX_ENDPOINT,
    protocol="http/protobuf",
    batch=True,
    auto_instrument=True,
)
tracer = trace.get_tracer(__name__)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)


SKILLS_DIR = Path(__file__).parent / "skills"
MAX_ATTEMPTS = 3


def resolve_skill_dir(name: str) -> Path:
    """Return the skill directory under `skills/` or fail fast if missing."""
    target = SKILLS_DIR / name
    if target.exists():
        return target

    raise FileNotFoundError(
        f"Missing skill directory: {target}. Create the obstacle skill under the skills folder."
    )


# ---------------------------------------------------------------------------
# Skill loading (stand-in for google.adk.skills.SkillToolset)
# ---------------------------------------------------------------------------

@dataclass
class Riddle:
    question: str
    answer: str


class ObstacleStoryAgent:
    """Reusable agent that tells a short obstacle-specific story."""

    def __init__(self) -> None:
        self._agent = LlmAgent(
            name="obstacle_storyteller",
            model=VICTORY_MODEL,
            instruction=(
                "You are a family-friendly story narrator for a cat adventure game. "
                "Use the obstacle skill text provided by the user to play the role exactly as described. "
                "Tell a short intro story in 2-3 sentences. "
                "Do not ask the riddle yet. "
                "Do not mention routes, attempts, or answers. "
                "Keep the tone warm, playful, and encouraging."
            ),
            output_schema=str,
        )

    async def _tell_story_async(self, obstacle_name: str, skill_text: str) -> str | None:
        session_service = InMemorySessionService()
        app_name = "cat_goes_home_game"
        user_id = "local_player"
        session_id = f"story_{obstacle_name}"

        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )

        runner = Runner(agent=self._agent, app_name=app_name,
                        session_service=session_service)
        content = genai_types.Content(
            role="user",
            parts=[
                genai_types.Part(
                    text=(
                        f"Obstacle skill for {obstacle_name}:\n\n"
                        f"{skill_text}\n\n"
                        "Now tell the short intro story for this obstacle."
                    )
                )
            ],
        )

        story_line = None
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        story_line = part.text.strip()

        return story_line

    async def tell_story(self, obstacle_name: str, skill_text: str) -> str:
        story_line = await self._tell_story_async(obstacle_name, skill_text)
        if not story_line:
            raise RuntimeError(
                f"Story agent did not return a story for {obstacle_name}.")
        return story_line


class VictoryAgent:
    """Tiny agent that returns a funny line when the cat gets home."""

    def __init__(self) -> None:
        self._agent = LlmAgent(
            name="victory_joker",
            model=VICTORY_MODEL,
            instruction=(
                "You are a funny cat narrator. "
                "Return exactly one short, family-safe, funny one-liner "
                "celebrating that a cat finally made it home. "
                "No emojis. No quotes. Max 20 words."
            ),
            output_schema=str,
        )

    async def _adk_celebrate(self) -> str | None:
        session_service = InMemorySessionService()
        app_name = "cat_goes_home_game"
        user_id = "local_player"
        session_id = "victory_session"

        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        )

        runner = Runner(agent=self._agent, app_name=app_name,
                        session_service=session_service)

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(
                text="The cat reached home safely. Give the one-liner now.")],
        )

        joke_line = None
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        joke_line = part.text.strip()

        return joke_line

    async def celebrate(self) -> str:
        joke_line = await self._adk_celebrate()
        if not joke_line:
            raise RuntimeError("Victory agent did not return a joke line.")
        return joke_line


def load_riddles(obstacle_dir: Path) -> list[Riddle]:
    """Parses references/riddles.txt into a list of Riddle objects."""
    path = obstacle_dir / "references" / "riddles.txt"
    text = path.read_text(encoding="utf-8")

    riddles = []
    blocks = re.split(r"RIDDLE \d+\n", text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        q_match = re.search(r"Question:\s*(.+)", block)
        a_match = re.search(r"Answer:\s*(.+)", block)
        if q_match and a_match:
            riddles.append(Riddle(question=q_match.group(1).strip(),
                                  answer=a_match.group(1).strip().lower()))
    return riddles


def load_skill_text(obstacle_dir: Path) -> str:
    """Reads the full SKILL.md so the story agent can follow the role and tone."""
    return (obstacle_dir / "SKILL.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Node definition
# ---------------------------------------------------------------------------

@dataclass
class ObstacleNode:
    name: str
    display_name: str
    skill_dir: Path
    skill_text: str = ""
    riddles: list[Riddle] = field(default_factory=list)
    attempts: int = 0
    asked: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, name: str, display_name: str):
        skill_dir = resolve_skill_dir(name)
        node = cls(name=name, display_name=display_name, skill_dir=skill_dir)
        node.skill_text = load_skill_text(skill_dir)
        node.riddles = load_riddles(skill_dir)
        return node

    def pick_riddle(self) -> Riddle:
        unused = [r for r in self.riddles if r.question not in self.asked]
        pool = unused if unused else self.riddles
        riddle = random.choice(pool)
        self.asked.append(riddle.question)
        return riddle

    async def ask(self, story_agent: ObstacleStoryAgent) -> str:
        """
        Runs one round at this obstacle: tell the obstacle story, ask a
        riddle, check the answer, update attempts, and return a route
        string ("CORRECT", "RETRY", or "FAILED_BACK").
        """
        story_line = await story_agent.tell_story(self.name, self.skill_text)
        print(f"\n✨ {story_line}")

        riddle = self.pick_riddle()
        print(f"\n🐾 {self.display_name}")
        print(f"Riddle: {riddle.question}")
        user_answer = input("Your answer: ").strip().lower()

        if user_answer == riddle.answer:
            self.attempts = 0
            print("✅ Correct! The cat moves forward.")
            return "CORRECT"

        self.attempts += 1
        if self.attempts >= MAX_ATTEMPTS:
            self.attempts = 0
            print(
                f"❌ Wrong {MAX_ATTEMPTS} times. The cat gets spooked and retreats!")
            return "FAILED_BACK"
        else:
            remaining = MAX_ATTEMPTS - self.attempts
            print(
                f"❌ Not quite. ({remaining} attempt(s) left before the cat backs off)")
            return "RETRY"


# ---------------------------------------------------------------------------
# Graph definition (nodes + edges)
# ---------------------------------------------------------------------------

def build_graph():
    obstacle_river = ObstacleNode.load(
        "obstacle_river", "Obstacle 1: The River")
    obstacle_fence = ObstacleNode.load(
        "obstacle_fence", "Obstacle 2: The Fence")
    obstacle_street = ObstacleNode.load(
        "obstacle_street", "Obstacle 3: The Busy Street")

    # This mirrors the edges=[...] list from google.adk.workflow.Workflow
    edges = {
        "START": {"NEXT": obstacle_river},

        "obstacle_river": {
            "CORRECT": obstacle_fence,
            "RETRY": obstacle_river,
            "FAILED_BACK": obstacle_river,  # no earlier obstacle, stays put
        },
        "obstacle_fence": {
            "CORRECT": obstacle_street,
            "RETRY": obstacle_fence,
            "FAILED_BACK": obstacle_river,
        },
        "obstacle_street": {
            "CORRECT": "HOME",
            "RETRY": obstacle_street,
            "FAILED_BACK": obstacle_fence,
        },
    }

    return obstacle_river, edges


# ---------------------------------------------------------------------------
# Runtime loop (stand-in for the ADK scheduler)
# ---------------------------------------------------------------------------

async def run_game():
    print("🐱 Cat Goes Home — the journey begins!\n")
    victory_agent = VictoryAgent()
    story_agent = ObstacleStoryAgent()

    current_node, edges = build_graph()

    with tracer.start_as_current_span("cat_game.run") as span:
        span.set_attribute("game.project", "cat-goes-home")

        while True:
            with tracer.start_as_current_span(f"game.{current_node.name}") as node_span:
                node_span.set_attribute("game.node", current_node.name)
                route = await current_node.ask(story_agent)
                node_span.set_attribute("game.route", route)

                next_step = edges[current_node.name][route]
                node_span.set_attribute("game.next_step", getattr(
                    next_step, "name", str(next_step)))

                if next_step == "HOME":
                    span.set_attribute("game.outcome", "won")
                    with tracer.start_as_current_span("game.victory_agent"):
                        funny_line = await victory_agent.celebrate()
                    print("\n🏠 The cat made it home! 🎉 Game over — you won!")
                    print(f"😹 {funny_line}")
                    tracer_provider.force_flush()
                    break

                current_node = next_step


if __name__ == "__main__":
    asyncio.run(run_game())
