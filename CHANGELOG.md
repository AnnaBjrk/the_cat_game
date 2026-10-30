# Ändringslogg

## v1.0 (inte taggad än)
Första spelbara versionen av Cat Lost.

### Spelet
- Innehållsfiler med frågor och berättelsetexter (`88ca4a9`, `3e7c854`)
- Förflyttning på spelplanen (`d65a298`)
- Frågor på frågerutorna (`fbb18f4`)
- Café, häxa och hem (`ddfd987`)
- Meddelanden och karta (`c3b3fac`)
- Terminalspel och vinstanimering (`f854784`)

### Ändringar efter provspelning
- Spelaren väljer om kakan ska ges till häxan, och rutan (1,4) är blockerad (`321f176`)
- Kartan visas före meddelandet efter varje drag (`567d0f5`)
- Hus visas som fylld fyrkant och har en egen text, och kartans kant har också en egen text (`949727e`, `fa27ac5`)
- En skärm i taget med ramad karta, sidopanel, fetstil och kursiv kommandorad (`43380d1`)

### Tester
- Prestandatester och kontroll av att inga AI-paket laddas (`f374da5`)

### Projektet
- Byggplan och uppdaterad spec (`96c9288`, `e23c50c`)
- Cat Goes Home arkiveras i `arkiv/`, och Cat Lost blir huvudspel (`760073b`)
- `.claude/` och planen anpassas till Cat Lost (`2c65882`)
- Agenten `question-writer` och krav på svarsalternativ (`154acf1`)
- Syntaxhooken kontrollerar också JSON, och `.DS_Store` spåras inte längre (`4470a74`, `77fe75d`)
- Tydligare regler i `CLAUDE.md` om defensiv kod och commit-meddelanden (`b66f191`, `64c9832`)

## Före v1.0
Det arkiverade spelet Cat Goes Home och projektets första struktur (`b9b1660`, `9e77301`, `d54f09d`).
