# ParkVieta – darbo taisyklės

Tai universiteto kursinis darbas („Programų sistemų projektavimas“). Kodą vertina dėstytojas pagal paskaitų reikalavimus, o studentas turi gebėti paaiškinti ir pakeisti kiekvieną kodo vietą. Šios taisyklės galioja KIEKVIENAM pakeitimui.

## Darbo eiga
- Dirbk mažais žingsniais: vienas pakeitimas → visi testai → ruff → diff → SUSTOK ir lauk patvirtinimo. Niekada nedaryk kelių užduoties punktų iš karto, net jei jie paprasti.
- Prieš keisdamas elgseną, pirmiausia parašyk arba atnaujink testą (TDD: raudona → žalia → refaktorinimas). Refaktorinimas elgsenos nekeičia – esami testai turi praeiti nepakeisti.
- Po kiekvieno pakeitimo paleisk VISUS testus: `python -m pytest -v` (DB turi veikti: `docker compose ps`), tada `ruff check .` ir `ruff format --check .`.
- Nekeisk `projektavimo-dokumentas.md` – tai pateiktas I etapo dokumentas. Nukrypimus nuo jo registruok `docs/pakeitimai-nuo-1-etapo.md`.
- Nepridėk naujų bibliotekų jų nesuderinęs. Neišjunginėk kitų procesų ir nekeisk sistemos be leidimo.
- Paaiškinimuose teik tik patikrintus teiginius. Jei nesi tikras, taip ir sakyk. Neperdėk („neįmanoma“, „garantuota“), jei tai priklauso nuo prielaidų.

## Švarus kodas
- Pavadinimai tikslūs ir iš domeno žodyno (spot, zone, tenant, parking, event): funkcijos – veiksmažodžiai arba is/has/can, klasės ir kintamieji – daiktavardžiai. Jokių trumpinių kaip t, s, r (išskyrus trumpas lambda išraiškas).
- Trumpos funkcijos, kiekviena daro vieną dalyką. Klasė turi vieną atsakomybę, kurią galima apibūdinti vienu sakiniu be „ir“.
- Jokių paslėptų šalutinių efektų: get_*, is_*, count_* metodai būsenos nekeičia.
- Jokio logikos dubliavimo – bendrą logiką iškelk į vieną vietą.
- Jokių magiškų skaičių ir tekstų – naudok enum arba pavadintas konstantas.
- Komentarai tik ten, kur pavadinimas negali paaiškinti „kodėl“. Jokio užkomentuoto kodo.
- Nuoseklumas visame projekte: tipų anotacijos (`str | None`, ne `Optional`), klaidų apdorojimas (servisas meta `ParkingError`, `process_event` grąžina `AllocationResult` su `REJECTED`), kodas ir pavadinimai angliškai, pranešimai naudotojui, docstring'ai ir komentarai lietuviškai.
- KISS ir YAGNI: paprasčiausias sprendimas, kuris išsprendžia dabartinę problemą. Šablonus ir abstrakcijas pridėk tik tada, kai jie sprendžia realią problemą.

## OOP ir SOLID
- Inkapsuliacija: vidinė būsena privati (`_`), išorė naudoja tik viešą API. Law of Demeter – jokių grandinių a.get_b().get_c().
- SRP, OCP (naujas vietos tipas – nauja `SpotEligibilityRule` klasė ir registracija, esamos klasės nekeičiamos), LSP (`InMemoryRepository` ir `PostgreSQLRepository` visiškai pakeičiamos, jokių isinstance tikrinimų), ISP, DIP (servisai ir API priklauso nuo `ParkingRepository` abstrakcijos; konkreti saugykla kuriama tik `app/api/dependencies.py`).
- Composition over inheritance. Priklausomybės perduodamos per konstruktorių.

## Architektūra
- Sluoksniai: `api → services → domain`, `repositories → domain`. Domenas nepriklauso nuo FastAPI ir SQLAlchemy.
- API ir sąsajoje (`static/index.html`) jokios verslo logikos.
- Klientų izoliacija: kiekviena saugyklos užklausa eina per tenant filtrus (`_zone_q`, `_spot_q`, `_parking_q`). Naujam metodui – izoliacijos testas.
- Transakcijos riba – tik `get_db` (`app/api/dependencies.py`).

## Testai
- Arrange–Act–Assert struktūra, atskirta tuščiomis eilutėmis. Vienas testas – viena elgsena. Pavadinimas aprašo elgseną ir laukiamą rezultatą.
- Tikrink konkrečias reikšmes (vietos numerį, klaidos kodą, laisvų vietų skaičių). Klaidos atveju patikrink, kad būsena nepasikeitė.
- Unit testai (`@pytest.mark.unit`) veikia atmintyje, nepriklauso nuo datos, laiko ir vykdymo eilės. Integraciniai (`@pytest.mark.integration`) naudoja `TEST_DATABASE_URL`.
- Testuose jokios verslo logikos. Tikrink ribinius atvejus ir klaidas.
- Testas turi nukristi, jei sugadinama jo tikrinama taisyklė – jokių testų, kurie praeitų nepriklausomai nuo kodo.
