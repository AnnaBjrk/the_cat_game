from typing import Literal

from google.adk import Workflow, Event
from google.adk.agents import LlmAgent
from google.adk.workflow import Edge
from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    route: Literal["CORRECT", "RETRY", "FAILED_BACK"] = Field(
        ...,
        description="Exactly one of CORRECT, RETRY, or FAILED_BACK.",
    )


def make_obstacle_agent(name, question_topic):
    return LlmAgent(
        name=name,
        instruction=f"""
        Ask the user a question related to: {question_topic}.
        Check session_state['attempts_{name}'] (default 0).

        You are a route-decider for this workflow. Return ONLY one exact word:
          - CORRECT
          - RETRY
          - FAILED_BACK

        Rules:
        1. If the answer is correct:
           - reset session_state['attempts_{name}'] to 0
           - output exactly: CORRECT
        2. If the answer is wrong:
           - increment session_state['attempts_{name}']
           - if attempts_{name} >= 3:
               - reset session_state['attempts_{name}'] to 0
               - output exactly: FAILED_BACK
           - else:
               - output exactly: RETRY

        Important:
        - Output ONLY the exact route word and nothing else.
        - No JSON, no quotes, no punctuation, no explanation.
        - The value must be one of the exact strings above.
        """,
        output_schema=str,
    )

obstacle_1_agent = make_obstacle_agent("obstacle_1", "crossing the river")
obstacle_2_agent = make_obstacle_agent("obstacle_2", "climbing the fence")
obstacle_3_agent = make_obstacle_agent("obstacle_3", "crossing the busy street")

# --- Alternative: load riddles from a Skill instead of inlining them ------
# Real ADK Python Skills API (google-adk >= 1.25.0, experimental):
#   - `load_skill_from_dir` reads a skill's SKILL.md + references/ from disk.
#   - `SkillToolset` (from google.adk.tools.skill_toolset) exposes the loaded
#     skill(s) to the agent via load_skill / load_skill_resource tools.
#   - There is no `AgentMode` in the Python SDK (that's a Go v2.0.0-only
#     concept); plain LlmAgent nodes used inside a Workflow already behave
#     like single-turn task steps.
#
# from pathlib import Path
# from google.adk.skills import load_skill_from_dir
# from google.adk.tools import skill_toolset
#
# SKILLS_DIR = Path(__file__).parent / "skills"
#
# def make_skill_based_obstacle_agent(name, skill_dir_name):
#     skill = load_skill_from_dir(SKILLS_DIR / skill_dir_name)
#     toolset = skill_toolset.SkillToolset(skills=[skill])
#
#     return LlmAgent(
#         name=name,
#         tools=[toolset],
#         instruction=f"""
#         Load the '{skill_dir_name}' skill and ask the user its riddle.
#         Check session_state['attempts_{name}'] (default 0).
#
#         If the answer is correct:
#           - reset session_state['attempts_{name}'] to 0
#           - output route='CORRECT'
#
#         If the answer is wrong:
#           - increment session_state['attempts_{name}']
#           - if attempts_{name} >= 3:
#               - reset session_state['attempts_{name}'] to 0
#               - output route='FAILED_BACK'
#           - else:
#               - output route='RETRY'
#         """,
#         output_schema=str,
#     )
#
# obstacle_agent = make_skill_based_obstacle_agent("obstacle_1", "obstacle_river")



def start_node(node_input=None):
    return Event(message="The cat begins its journey home!")

def home_node(node_input=None):
    return Event(message="🐱 The cat made it home! Game over — you won!")


root_agent = Workflow(
    name="cat_goes_home_game",
    edges=[
        ("START", start_node, obstacle_1_agent),

        (obstacle_1_agent, {
            "CORRECT": obstacle_2_agent,
        }),
        # RETRY and FAILED_BACK both loop back to obstacle_1 itself, so they
        # must be combined into one edge (two edges with the same
        # from/to pair are rejected as duplicates by graph validation).
        Edge(
            from_node=obstacle_1_agent,
            to_node=obstacle_1_agent,
            route=["RETRY", "FAILED_BACK"],  # ingen tidigare obstacle finns, stannar kvar
        ),

        (obstacle_2_agent, {
            "CORRECT": obstacle_3_agent,
            "RETRY": obstacle_2_agent,
            "FAILED_BACK": obstacle_1_agent,  # skickas tillbaka!
        }),

        (obstacle_3_agent, {
            "CORRECT": home_node,
            "RETRY": obstacle_3_agent,
            "FAILED_BACK": obstacle_2_agent,  # skickas tillbaka!
        }),
    ],
)
