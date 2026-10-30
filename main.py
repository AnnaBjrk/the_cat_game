"""
Local CLI runner for the Cat Goes Home ADK agent.

The agent itself lives in cat_goes_home/agent.py, following the standard ADK
project layout so it can also be launched with the ADK dev tooling:

    adk web .          # dev UI, run from the_cat_game/ (auto-discovers
                        # any subfolder with an __init__.py + root_agent)
    adk run cat_goes_home

This script is an alternative for running the exact same root_agent directly
with `python main.py`, without needing the `adk` CLI installed on PATH.

to install phoenix 
uvx arize-phoenix serve
pip install arize-phoenix

to run phoenix
phoenix serve

http://localhost:6006
"""

from cat_goes_home.agent import root_agent
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

import os
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

# .env lives next to this script, in the project root. load_dotenv() searches
# upward from this file's folder, so it finds it from any working directory.
load_dotenv()


APP_NAME = "cat_goes_home_game"
USER_ID = "local_player"
SESSION_ID = "local_session"
PHOENIX_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")


async def main():

    # initialize the tracing provider once; let Phoenix handle the ADK instrumentation
    tracer_provider = register(
        project_name="cat-goes-home",
        endpoint=PHOENIX_ENDPOINT,
        auto_instrument=True,
        set_global_tracer_provider=False,
    )

# create a session service and runner for the root_agent
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    runner = Runner(agent=root_agent, app_name=APP_NAME,
                    session_service=session_service)

    print("🐱 Cat Goes Home — the journey begins! (type 'quit' to exit)\n")

    user_text = "Let's begin!"
    while True:
        content = types.Content(
            role="user", parts=[types.Part(text=user_text)])

        async for event in runner.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=content
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}] {part.text.strip()}")

        user_text = input("\nYour answer (or 'quit'): ").strip()
        if user_text.lower() == "quit":
            print("Goodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
