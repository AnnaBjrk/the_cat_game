---
name: add-obstacle
description: Adds a new obstacle to the Cat Goes Home game. Use when the user wants a new obstacle or game level.
---

# Add an obstacle

1. Create `skills/obstacle_<name>/SKILL.md`, using an existing obstacle as the model.
2. Create `skills/obstacle_<name>/references/riddles.txt` in the same format as the existing files.
3. Load the obstacle in `build_graph()` in `game.py` and connect its edges.
