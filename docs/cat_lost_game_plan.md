# Plan: Cat Lost, version 1

Planen beskriver hur spelet byggs. Reglerna och kraven står i [specen](cat_lost_game_spec.md), som gäller om filerna säger olika.

## Arkitektur
Koden ligger i `cat_lost_game.py` och är uppdelad i fyra lager:

```text
JSON-filer → load_content() → Regler → Text → Terminal
                              (rena)   (rena)  (input/print)
```

| Lager | Ansvar | Viktigaste funktioner |
|---|---|---|
| Innehåll | Läser och validerar JSON, stoppar med tydligt fel | `load_content()` |
| Regler | Tar emot spelarens val och returnerar resultat och tillstånd | `new_game()`, `step()` |
| Text | Gör om resultat till text och ritar kartan | `message_for()`, `render_map()` |
| Terminal | Enda stället med `input()`, `print()` och animering | `main()`, `play_win_animation()` |

### Designval
- **Tillstånd:** `GameState` är en dataklass med position, föregående position, kaka, upptäckta rutor, om häxan har fått sin kaka, fas, frågekö och slumpgenerator.
- **Faser:** spelet är i `MOVE`, `ANSWER_QUESTION`, `CHOOSE_CAKE`, `WON` eller `QUIT`. `step()` tolkar inmatningen utifrån fasen, så att reglerna aldrig väntar på `input()`.
- **Resultat:** `step()` returnerar en `Outcome`, till exempel `BLOCKED` eller `WITCH_WRONG`, och aldrig färdig text. Version 2 kan då byta ut `message_for()` och version 3 kan anropa `step()` direkt.
- **Slump:** `new_game()` tar emot en `random.Random`, så att testerna kan styra slumpen med ett eget frö.

## Byggordning
Varje del börjar med tester och avslutas med en commit. Kryssrutan bockas av i samma commit. Testerna körs med `python3 -m unittest`.

- [x] **1. Innehåll:** `cat_lost_story.json`, `cat_lost_questions.json` med minst 10 frågor och `load_content()`. Kraven på frågor och texter kontrolleras i testerna, inte när spelet startar. Frågorna skrivs med agenten `question-writer` och innehållet granskas med agenten `riddle-reviewer`.
- [ ] **2. Förflyttning:** karta, kommandon, väggar och kanter, upptäckta rutor och `avsluta`.
- [ ] **3. Frågor:** fasbyte, frågekö utan upprepning och att fel svar skickar tillbaka katten.
- [ ] **4. Café och häxa:** kakval, inventory och `leave`. Hela vägen hem spelas i ett test.
- [ ] **5. Text och karta:** `message_for()` och `render_map()`.
- [ ] **6. Terminal:** spelloopen och vinstanimeringen. `.claude/commands/smoke-test.md` skrivs om så att den startar spelet och kör `avsluta`.
- [ ] **7. Avslut:** prestandatester, kontroll av specens "Klart när", provspelning för hand och den nya filen i `CLAUDE.md`.

## Att tänka på
- `arkiv/game.py` startar Phoenix och ADK när den importeras, så `cat_lost_game.py` får inte importera från den.
