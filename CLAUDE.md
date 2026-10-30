# Cat Lost

The main game: the player guides a lost cat home across a 5x5 grid, answering questions and bringing the witch her favourite cake. Version 1 is plain Python with no AI. See `docs/` for the spec and build plan.

The earlier game, Cat Goes Home, is archived in `arkiv/`. It is a riddle game built with Google ADK and traced with Arize Phoenix.

## Layout

- `cat_lost_game.py`: rules, texts, and terminal interface for Cat Lost
- `cat_lost_questions.json` and `cat_lost_story.json`: questions and story texts
- `test_cat_lost_game.py`: tests
- `docs/`: spec and build plan for Cat Lost. Read both before working on it.
- `CHANGELOG.md`: changes per version, with commit ids
- `arkiv/`: the archived Cat Goes Home game
- `arkiv/game.py`: self-contained game loop that reads riddles from `arkiv/skills/`
- `arkiv/main.py`: CLI runner for the ADK workflow agent
- `arkiv/cat_goes_home/agent.py`: the ADK workflow (`root_agent`)
- `arkiv/skills/`: game content used by the ADK agents. These are not Claude Code skills, which live in `.claude/skills/`.

## Commands

- Play Cat Lost: `python3 cat_lost_game.py`
- Run the tests: `python3 -m unittest`

These commands are for the archived game. Cat Lost version 1 needs no installed packages.

- Install: `pip install -r requirements.txt`
- Play the archived game: `python arkiv/game.py`
- Run the ADK agent: `python arkiv/main.py` or `adk web arkiv`
- Start tracing: `phoenix serve`, then open http://localhost:6006

## Conventions

- Keep the game family-friendly.
- Secrets live in `.env`. Never read or commit this file.
- Prefer readable code over defensive code. Don't add fallbacks, default values, or extra checks; let failures surface as errors with a clear message.
- Add a runtime check only when the spec asks for it. Tests check what we control, such as the content files in this repo, so the game doesn't check them again when it starts.
- Never hardcode a value to work around a problem. Fix the cause.
- Write commit messages in Swedish with a heading and a few lines on what changed and why. When reporting a commit in chat, give the heading and then the commit id.
- When game behaviour changes, update the spec in the same commit. Then add the change to `CHANGELOG.md` with its commit id in a follow-up commit, since a commit can't contain its own id.
