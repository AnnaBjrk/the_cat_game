# Spec: Cat Lost (`cat_lost_game.py`)

## 1. Sammanfattning
En häxa har trollat bort en katt, som vaknar vilse på en öde parkering. Spelaren hjälper katten hem på en spelplan med 5x5 rutor. Katten flyttas en ruta i taget, svarar på frågor och måste ge häxan hennes favoritkaka för att komma hem. Spelaren får ett meddelande varje tur, och allt i spelet är på svenska.

| Version | Innehåll | Status |
|---|---|---|
| 1 | Spelet i ren Python, utan AI | Ska byggas nu |
| 2 | AI-berättare ovanpå samma regler | Ska inte byggas nu, se avsnitt 12 |
| 3 | Ett UI med en interaktiv spelplan | Ska inte byggas nu, se avsnitt 12.1 |

### Effektmål
- **Lätt att förstå:** en ny spelare kan spela klart utan instruktioner från någon annan.
- **Lagom lång omgång:** en omgång tar cirka 3-5 minuter.
- **Roligt att utforska:** de dolda rutorna och berättelsen gör att spelaren vill testa olika vägar.
- **Bra grund för version 2:** AI kan läggas till utan att spelreglerna ändras.
- **Övning i arbetssättet:** spelet byggs med explore-plan-code-commit.

### Utanför scope
Spara spel, flera kartor, poäng och flerspelarläge ingår inte.

## 2. Filer (version 1)
| Fil | Innehåll |
|---|---|
| `cat_lost_game.py` | Spelregler och terminalgränssnitt |
| `cat_lost_questions.json` | Frågor och svar |
| `cat_lost_story.json` | Berättelsens texter och miljöbeskrivningar |
| `test_cat_lost_game.py` | Tester |

## 3. Spelplan
Spelplanen är en lista av listor. Varje inre lista är en rad och positioner skrivs `(rad, kolumn)` med `grid[row][col]`. Rad 0 är överst och kolumn 0 längst till vänster. Rutornas namn i koden är på engelska.

```python
GRID = [
    ["start",    "free",     "free",    "free",    "fetch"],
    ["free",     "free",     "blocked", "blocked", "blocked"],
    ["free",     "question", "free",    "free",    "blocked"],
    ["free",     "blocked",  "blocked", "leave",   "home"],
    ["question", "free",     "free",    "blocked", "blocked"],
]
```

Viktiga positioner:
- Katten börjar på `start` (0,0).
- `fetch` ligger på (0,4), `leave` på (3,3) och `home` på (3,4).
- `question` på (2,1) går inte att runda på vägen hem.
- `question` på (4,0) leder till en återvändsgränd som spelaren kan råka gå in i. Den ger ingen belöning.

## 4. Förflyttning
- Kommandon: `upp`, `ner`, `vänster`, `höger` och `avsluta`. Ett steg per kommando.
- `avsluta` fungerar alltid, även under en fråga eller ett kakval.
- Stor eller liten bokstav spelar ingen roll, och mellanslag före och efter ignoreras.
- Ogiltigt kommando: meddelande och ny fråga. Katten står kvar.
- Utanför kartan eller `blocked`: katten står kvar och får meddelandet i avsnitt 9.

## 5. Rutor
| Ruta | Vad som händer när katten går in |
|---|---|
| `start` | Spelaren väljer nästa steg. Berättelsen visas bara när spelet startar. |
| `free` | Spelaren väljer nästa steg. |
| `blocked` | Katten kan inte gå dit. |
| `question` | En fråga ställs, se avsnitt 6. |
| `fetch` | Spelaren måste välja en kaka, se avsnitt 7. |
| `leave` | Häxan vill ha sin favoritkaka, se avsnitt 8. |
| `home` | Spelet är vunnet. Vinstanimeringen spelas och spelet avslutas, se avsnitt 10.1. |

**Skickas tillbaka:** katten flyttas till rutan den senast kom från. Rutan utlöser inget nytt när katten kommer tillbaka.

**Ingen förlust:** spelet kan inte förloras. Spelaren försöker tills katten är hemma eller avslutar med `avsluta`.

## 6. Frågor
- Varje fråga har exakt 4 svarsalternativ, och spelaren svarar med `1`-`4`.
- Alternativen visas i slumpad ordning.
- Rätt svar: katten står kvar på rutan och spelaren väljer nästa steg.
- Fel svar: katten skickas tillbaka.
- Ogiltigt svar: spelaren får svara igen, utan straff.
- En ny fråga ställs **varje gång** katten går in på en frågeruta, även en ruta som redan klarats.
- Frågor slumpas utan upprepning. När alla har använts börjar listan om.
- Frågorna finns i `cat_lost_questions.json`:

```json
[
  {
    "question": "Vilket djur säger mjau?",
    "choices": ["Hund", "Katt", "Ko", "Anka"],
    "answer": "Katt"
  }
]
```

Krav på filen: minst 10 frågor på svenska, familjevänligt innehåll, och `answer` måste finnas bland `choices`.

Svarsalternativen i en fråga ska vara ungefär lika långa, så att längden inte avslöjar rätt svar. Har ett alternativ ett förtydligande eller exempel ska de andra också ha det. Skriv till exempel "Hund", "Katt", "Ko", "Anka", inte "Hund", "Katt, ett litet rovdjur", "Ko", "Anka".

## 7. Fetch och inventory
- Kakor: `kanelbulle`, `chokladboll`, `prinsesstårta`, `morotskaka`, `äppelpaj`.
- Inventory är en lista som rymmer högst **en** kaka.
- Utan kaka väljer spelaren bland alla 5.
- Med kaka väljer spelaren bland de 4 andra, och den gamla kakan lämnas tillbaka.
- Samma kakor erbjuds varje gång. Bara den kaka katten redan bär tas bort från listan.
- Spelaren väljer med en siffra. Ogiltigt val ger en ny fråga.
- Spelaren måste välja. Det går inte att avstå.
- Valet ställs varje gång katten går in på rutan.

**Följd av reglerna:** en katt som bär `äppelpaj` och går in på `fetch` igen tvingas byta bort den. Spelaren kan hämta den igen genom att gå av och på rutan.

## 8. Leave (häxan)
Häxans favoritkaka är alltid `äppelpaj`. Bär katten en kaka frågas spelaren om den ska ges till häxan och svarar `ja` eller `nej`. Frågan ställs för alla kakor, så att den inte avslöjar vilken som är rätt. Ogiltigt svar ger en ny fråga.

| Katten bär | Spelaren svarar | Resultat |
|---|---|---|
| `äppelpaj` | `ja` | Kakan ges bort, inventory blir tomt och rutan öppnas. Katten står kvar och väljer nästa steg. |
| En annan kaka | `ja` | Katten flyttas till `start` och behåller kakan. |
| Valfri kaka | `nej` | Katten skickas tillbaka och behåller kakan. |
| Ingen kaka | Får ingen fråga | Katten flyttas till `start`. |

När häxan har fått sin kaka fungerar `leave` som `free` resten av spelet.

## 9. Meddelanden
Varje tur får spelaren ett meddelande. Logiken är att varje drag ger ett resultat, och resultatet avgör vilken text som visas. Det gör att spelreglerna inte behöver känna till texterna, och att AI kan ta över texterna i version 2.

| Resultat | Text |
|---|---|
| Spelet startar | `start_story`, följt av kommandona |
| `blocked` | `blocked` |
| Utanför kartan | `off_map` |
| `free`, en öppnad `leave` eller att gå till `start` igen | En slumpad text från `free_descriptions` |
| `question` | `question_intro` följt av frågan |
| Rätt eller fel svar | `question_correct` eller `question_wrong` |
| `fetch` | `fetch` följt av kakorna |
| `leave` när katten bär en kaka | `leave` följt av `witch_offer` |
| Häxan får rätt kaka | `witch_correct` |
| Häxan får fel kaka | `witch_wrong` |
| Spelaren svarar `nej` | `witch_declined` |
| `leave` när katten saknar kaka | `leave` följt av `witch_no_cake` |
| `home` | `home` |

Texterna finns i `cat_lost_story.json`:

```json
{
  "start_story": "En häxa knackade på kattens hus och sen blev allt dimmigt. Han vaknar här på den här öde parkeringen, blöt och smutsig, och vill bara hem. Men han vet inte var han är... Katten tittar sig omkring och funderar: vart ska han gå?",
  "blocked": "Katten försöker gå in i ett hus, men det går inte. Dörren är stängd.",
  "off_map": "Här tar staden slut, och katten kan inte gå längre åt det hållet.",
  "free_descriptions": [
    "En bil far förbi, sen är allt öde.",
    "Det börjar regna igen och vår katt fryser.",
    "Husen blir högre och högre, och det finns ingen att fråga.",
    "En man skyndar förbi men svarar inte när katten frågar om vägen.",
    "En lampa blinkar i regnet, en hund skäller bakom en dörr."
  ],
  "fetch": "Du går in på ett café som ser öppet ut och frågar efter vägen. Mannen bakom disken vet inte vart du ska gå. Men han bjuder på en kopp te och ber dig ta något att äta. Du är inte hungrig men tar med en kaka. Vilken väljer du?",
  "leave": "Det här är en gata du känner igen!! Snart är du hemma. Men precis då dyker häxan upp. Hon har stått och väntat på dig bakom en buske. Ha ha, säger hon. Du trodde att du skulle komma hem så lätt. He, he... För att det är kul ska jag ge dig en chans att få komma förbi. Om du misslyckas trollar jag bort dig i staden igen. Jag börjar bli hungrig. Om du ger mig min favoritkaka får du komma hem.",

  "question_intro": "En gammal katt på en mur spärrar vägen. Svara rätt, säger den, så får du gå vidare.",
  "question_correct": "Rätt! Den gamla katten nickar och flyttar på sig.",
  "question_wrong": "Fel! Den gamla katten fräser och du får gå tillbaka.",
  "witch_offer": "Vill du ge häxan din {cake}? (ja/nej)",
  "witch_declined": "Du behåller kakan och backar undan. Jag väntar här, ropar häxan efter dig.",
  "witch_correct": "Mmm, äppelpaj! Häxan smaskar nöjt och försvinner in bakom busken. Vägen hem är fri.",
  "witch_wrong": "Fy, den kakan tycker jag inte om! Häxan viftar med handen och allt blir dimmigt. Du vaknar på parkeringen igen.",
  "witch_no_cake": "Har du ingen kaka med dig? Häxan viftar med handen och allt blir dimmigt. Du vaknar på parkeringen igen.",
  "home": "Där är ditt hus! Katten slinker in genom dörren, torr, trygg och äntligen hemma."
}
```

## 10. Vad spelaren ser
Kartan skrivs ut före varje drag:
- Kattens plats är markerad.
- Innehållet i en ruta visas först när katten har besökt den eller försökt gå in på den, till exempel en `blocked`-ruta.
- Rutor som inte har upptäckts visas som `?`.
- Rutorna visas på svenska: `start`, `fri`, `fråga`, `café`, `häxa`, `hem`. Ett hus (`blocked`) visas som en fylld fyrkant: `■`.
- Inventory visas tillsammans med kartan.
- Alla rutor är 5 tecken breda.
- Ordningen är karta, kaka, tom rad, meddelande och sist frågan om vart katten ska gå.

Exempel:
```text
[katt ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]
[  ?  ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]
[  ?  ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]
[  ?  ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]
[  ?  ] [  ?  ] [  ?  ] [  ?  ] [  ?  ]
Kaka: ingen

En bil far förbi, sen är allt öde.
Vart vill du gå? (upp/ner/vänster/höger/avsluta):
```

### 10.1 Vinstanimering
När katten når `home` dansar en gul/orange ASCII-katt i terminalen.
- Animeringen har minst 2 bilder som växlar och pågår i cirka 3 sekunder. Därefter visas texten `home` och spelet avslutas.
- Färgen görs med ANSI-koder och återställs när animeringen är klar.
- Animeringen ligger i en egen funktion, så att testerna av spellogiken inte behöver köra den.

## 11. Krav på koden (version 1)
- Endast Pythons standardbibliotek. Ingen AI, inga API-nycklar och ingen spårning.
- Spellogiken ska ligga skild från `input()` och `print()`, så att den kan testas utan terminal och senare användas av ett UI.
- Spellogiken tar emot spelarens val och returnerar resultatet och spelets tillstånd. Bara terminalgränssnittet läser in och skriver ut.
- Ingen startkod på toppnivå: spelet startar bara under `if __name__ == "__main__":`.
- Slumpen ska gå att styra i tester.
- Importera inte från `arkiv/game.py`, eftersom den startar Phoenix och ADK när den importeras.
- Filerna under `arkiv/` ändras inte.
- Lättläst kod går före defensiv kod. Inga fallbacks: om något går sönder ska spelet stoppa med ett tydligt felmeddelande.
- Hårdkoda aldrig ett värde för att komma runt ett problem. Åtgärda orsaken.
- Spelets regler, som kartan och att `äppelpaj` är rätt kaka, är tillåtna värden i koden. De ska vara namngivna konstanter.

### Prestanda
- Spelet startar på under 1 sekund, vilket kräver att inga AI-paket laddas.
- Spelet svarar direkt efter varje kommando, i praktiken under 100 ms.
- Alla tester körs på under 2 sekunder, utan nätverk.
- Animeringen pågår i cirka 3 sekunder och fungerar i ett terminalfönster på 80 tecken.

### Klart när
Testerna använder `unittest` och täcker följande:
- [x] Vägen hem går att spela: till `fetch`, välj `äppelpaj`, tillbaka till (0,1), ned till frågan på (2,1), höger till (2,3), ned till `leave`, höger till `home`.
- [x] Vägg, kanten av kartan och ogiltiga kommandon flyttar inte katten och ger rätt meddelande.
- [x] Fel svar skickar tillbaka katten från båda riktningarna, och en frågeruta ställer en ny fråga vid nästa besök.
- [x] `fetch` visar 5 alternativ utan kaka och 4 med kaka, och inventory har aldrig mer än en kaka.
- [x] `leave` släpper bara förbi `äppelpaj`. Fel kaka eller ingen kaka flyttar katten till `start`, och fel kaka finns kvar i inventory.
- [x] `leave` frågar om kakan ska ges bort när katten bär en kaka. `nej` skickar tillbaka katten med kakan kvar, och ogiltigt svar ger en ny fråga.
- [x] `leave` fungerar som `free` när häxan har fått sin kaka.
- [x] `home` kan inte nås utan att häxan har fått sin kaka.
- [x] Varje typ av resultat ger rätt text, och berättelsen på `start` visas bara när spelet startar.
- [x] Rutor visas först efter besök eller försök att gå in.
- [x] JSON-filen har minst 10 frågor, varje fråga har exakt 4 svarsalternativ och `answer` finns bland `choices`.
- [x] En saknad eller ogiltig JSON-fil ger ett tydligt felmeddelande.
- [x] Spelet startar och går att avsluta med `avsluta`, även under en fråga och ett kakval.
- [x] Alla rutor på kartan är 5 tecken breda.
- [x] Kommandon fungerar oavsett stor eller liten bokstav och med mellanslag runt, inklusive `vänster` och `höger`.
- [x] Frågor upprepas inte förrän alla har använts, och ett ogiltigt svar ger inget straff.
- [x] När katten skickas tillbaka utlöser rutan inget nytt.
- [x] Katten kan ta sig ut ur återvändsgränden via frågan på (4,0).
- [x] `fetch` erbjuder samma kakor varje gång, utan den kaka katten bär, och ogiltigt val ger en ny fråga.
- [x] Alla texter i avsnitt 9 finns i `cat_lost_story.json`, och fria rutor ger en text från `free_descriptions`.
- [x] Spellogiken kan spela hela vägen hem utan `input()` och `print()`.
- [x] `cat_lost_game.py` laddar inga AI-paket, spelet startar på under 1 sekund och alla tester körs på under 2 sekunder.

Kontrolleras för hand:
- **Animeringen:** katten är gul/orange och dansar, pågår i cirka 3 sekunder och terminalens färger är normala efteråt.
- **Provspelning:** en ny spelare spelar klart utan hjälp, och omgången tar cirka 3-5 minuter.
- **Innehållet:** frågor och texter är familjevänliga och utan stavfel, och svarsalternativen i varje fråga är ungefär lika långa.

## 12. Version 2 (ska inte byggas nu)
Spelaren väljer tre saker när spelet startar:
- **Tema:** stad, land, berg eller hav
- **Tid:** nutid, framtid, medeltid eller stenålder
- **Stämning:** läskigt, roligt, vilsamt eller poetiskt

AI:n använder valen för att skapa stämning:
- Vid varje förflyttning beskriver den omgivningen och hur den förändras.
- Vid varje uppgift hittar den på en karaktär som ställer frågan, ger kakor eller ber om kakan.

Gränser för AI:n:
- Spelreglerna från version 1 gäller oförändrade. Koden, inte AI:n, avgör vad som är rätt och vart katten får gå.
- Frågor, svar och uppgifter är desamma och kommer från samma källor.
- AI:n får inte avslöja rutor som spelaren inte har upptäckt.
- Texten ska vara familjevänlig, även med stämningen "läskigt".
- Spelet använder ADK, som `arkiv/game.py`.
- Från och med version 2 spåras spelet med Phoenix. Spårningen behålls i version 3.

Prestanda:
- AI-text ska visas inom cirka 5 sekunder.
- Om AI:n inte svarar stoppar spelet med ett tydligt felmeddelande.
- Kostnaden per omgång mäts med hjälp av Phoenix.

### 12.1 Version 3 (ska inte byggas nu)
Spelet får ett UI med en interaktiv spelplan. UI:t använder samma spellogik som terminalversionen och innehåller inga egna spelregler.

Version 1 förbereds bara genom att spellogiken hålls skild från gränssnittet, se avsnitt 11. Inget UI-ramverk eller annan UI-kod läggs till i förväg.

## 13. Öppna frågor
Båda gäller version 2 och hindrar inte version 1:
1. Ditt svar på fråga 8 slutade mitt i meningen, "men användaren ska". Specen utgår från din beskrivning av version 2 ovan.
2. Häxan, parkeringen och affären hör till en stad. Hur ska de fungera om spelaren väljer till exempel temat hav eller tiden stenålder?
