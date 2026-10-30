---
name: obstacle-street
description: >
  Asks the player a riddle to help the cat cross the busy street, the
  final obstacle before home. Tracks failed attempts and signals whether
  the cat should reach home, retry, or fall back to the fence obstacle.
---

# Obstacle: The Busy Street

## Context

The cat is one obstacle away from home, but a busy street stands in the
way. To cross safely, the player must answer a riddle correctly. Three
failed attempts in a row send the cat back to the fence obstacle.

## Instructions

1. Check `session_state['attempts_obstacle_street']`. If it doesn't
   exist, initialize it to `0`.

2. Pick ONE riddle from `references/riddles.txt` not already asked this
   session (track via `session_state['asked_obstacle_street']`, a list).
   Repeat one if all have been used.

3. Present the riddle warmly, without revealing the answer. This is the
   hardest obstacle, so the riddle should feel slightly more challenging
   than the previous two.

4. Wait for the player's response.

5. Compare the response to the riddle's answer, accepting minor spelling
   variations and case-insensitive matches.

6. Based on the result:
   - **Correct:**
     - Reset `session_state['attempts_obstacle_street']` to `0`.
     - Respond with an excited line — the cat is almost home!
     - Output `route="CORRECT"`.
   - **Incorrect:**
     - Increment `session_state['attempts_obstacle_street']`.
     - If `>= 3`:
       - Reset the counter to `0`.
       - Respond that the cat got spooked by the traffic and scurried
         back to the fence to hide for a while.
       - Output `route="FAILED_BACK"`.
     - Else:
       - Give a short hint without revealing the answer.
       - Output `route="RETRY"`.

## Output Format

Always end your turn with one of:
- `route="CORRECT"`
- `route="RETRY"`
- `route="FAILED_BACK"`

## Tone Guidelines

Friendly, playful, all-ages. Frame wrong answers as the cat "thinking it
over," never as failure.
