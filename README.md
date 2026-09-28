# ParkVieta

SaaS sistema parkavimo aikštelių valdytojams. Pagal įvažiavimo ir išvažiavimo įvykius ji skaičiuoja laisvas vietas zonose ir atvykstančiam automobiliui parenka tinkamiausią laisvą vietą.

Kursinis darbas, modulis „Programų sistemų projektavimas“.

## Projekto būsena

| Etapas | Rezultatas | Būsena |
|---|---|---|
| I. Projektavimo dokumentas | [projektavimo-dokumentas.md](projektavimo-dokumentas.md) | Pateikta |
| II. Veikiantis prototipas | Pagrindinis modulis, automatiniai testai, du klientai | Planuojama |
| III. Galutinis sprendimas | Pilna sistema, kokybės atributų įrodymai, architektūros dokumentas | Planuojama |

## Pagrindinės funkcijos

- **Įvykių registravimas ir tikrinimas** – įvažiavimai ir išvažiavimai tikrinami, neteisingi įvykiai atmetami nekeičiant užimtumo.
- **Vietos paskyrimas** – parenkama tinkamiausia laisva vieta pagal vietos tipą (paprasta, elektromobilių, neįgaliųjų) ir atstumą iki įėjimo; pilnos zonos atveju siūloma kita zona.
- **Užimtumo peržiūra** – laisvų ir užimtų vietų skaičius pagal zonas.
- **Kelių klientų palaikymas** – kiekvieno aikštelės valdytojo duomenys atskirti sistemos logikos lygmeniu.

## Planuojamos technologijos

- Python 3.12, FastAPI
- PostgreSQL
- pytest
- Docker Compose (III etapas)

## Paleidimas

Paleidimo ir testų komandos, reikalingi įrankiai, pavyzdiniai duomenys ir demonstravimo žingsniai bus aprašyti II etape, kai bus įkeltas prototipo kodas.

## Dokumentacija

- [I etapo projektavimo dokumentas](projektavimo-dokumentas.md) – problema, apimtis, pagrindinio modulio taisyklės, testų scenarijai, kokybės atributai, sistemos struktūra ir darbų planas.
