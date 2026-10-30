# Cat Goes Home

A riddle game: the player helps a cat get home by answering a riddle at each obstacle (river, fence, busy street). Built with Google ADK and traced with Arize Phoenix.

## Layout

- `game.py`: self-contained game loop that reads riddles from `skills/`
- `main.py`: CLI runner for the ADK workflow agent
- `cat_goes_home/agent.py`: the ADK workflow (`root_agent`)
- `skills/`: game content used by the ADK agents. These are not Claude Code skills, which live in `.claude/skills/`.
- `docs/`: spec and build plan for Cat Lost, the next game. Read both before working on it.

## Commands

- Install: `pip install -r requirements.txt`
- Play the game: `python game.py`
- Run the ADK agent: `python main.py` or `adk web .`
- Start tracing: `phoenix serve`, then open http://localhost:6006

## Conventions

- Keep the game family-friendly.
- Secrets live in `.env`. Never read or commit this file.
- Prefer readable code over defensive code. Don't add fallbacks; let failures surface as errors with a clear message.
- Never hardcode a value to work around a problem. Fix the cause.
