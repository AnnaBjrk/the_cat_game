---
name: obstacle-fence
description: >
  Asks the player a riddle to help the cat climb over the fence obstacle.
  Tracks failed attempts and signals whether the cat should advance,
  retry, or fall back to the previous obstacle (the river).
---

# Obstacle: The Fence

## Context

The cat has crossed the river and now faces a tall garden fence. To climb
over, the player must answer a riddle correctly. Three failed attempts in
a row send the cat back to the river obstacle.

## Instructions

1. Check `session_state['attempts_obstacle_fence']`. If it doesn't exist,
   initialize it to `0`.

2. Pick ONE riddle from `references/riddles.txt` not already asked this
   session (track via `session_state['asked_obstacle_fence']`, a list).
   Repeat one if all have been used.

3. Present the riddle warmly, without revealing the answer.

4. Wait for the player's response.

5. Compare the response to the riddle's answer, accepting minor spelling
   variations and case-insensitive matches.

6. Based on the result:
   - **Correct:**
     - Reset `session_state['attempts_obstacle_fence']` to `0`.
     - Respond with a short celebratory line.
     - Output `route="CORRECT"`.
   - **Incorrect:**
     - Increment `session_state['attempts_obstacle_fence']`.
     - If `>= 3`:
       - Reset the counter to `0`.
       - Respond that the cat got tired and climbed back down toward the
         river to rest.
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
