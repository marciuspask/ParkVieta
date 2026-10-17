# Kodo kokybės auditas – ParkVieta

**Data:** 2026-10-17  
**Auditorius:** Claude Sonnet 4.6 (automatinis)  
**Peržiūrėta:** visi `.py` failai (25 vnt.), testai (13 unit + integraciniai)

---

## 1. Švaraus kodo taisyklės

### 1.1 Nuoseklus formatavimas

⚠️ **Yra problemų**

`ruff` nėra įdiegtas projekte ir nėra `requirements.txt` srautu (`ruff check`, `ruff format --check` žlunga su „No module named ruff").

**Siūlomas pataisymas:** pridėti į `requirements.txt`:
```
ruff==0.9.0
```
ir į repozitoriją – `pyproject.toml` arba `ruff.toml`:
```toml
[tool.ruff]
line-length = 100
```
Pats kodas vizualiai yra tvarkingai suformatuotas, tačiau be automatinio tikrinimo tai negali būti garantuojama.

---

### 1.2 Prasmingi, tikslūs pavadinimai

⚠️ **Yra smulkių problemų**

**Gerai:**
- Funkcijų pavadinimai – veiksmažodžiai: `process_event`, `claim_spot`, `mark_spot_free`, `count_free_spots` ✅
- `is_eligible`, `is_occupied`, `has_disability_permit` – `is/has` prefiksai ✅
- Klasių pavadinimai – daiktavardžiai: `ParkingAllocationService`, `InMemoryRepository` ✅
- Domeno žodynas: `spot`, `zone`, `tenant`, `plate`, `parking` naudojamas nuosekliai ✅

**Problema – vienabukstančiai kintamieji:**

| Failas | Eilutė | Trumpinys | Kontekstas |
|---|---|---|---|
| `in_memory.py` | 24 | `z` | `lambda z: z.priority` |
| `postgres.py` | 36 | `r` | `[self._to_spot(r) for r in rows]` |
| `parking_allocation.py` | 132 | `s` | `lambda s: (s.distance_to_entrance, ...)` |
| `db/seed.py` | 13–16 | `s` (session) | `with Session(engine) as s:` |

Lambda kontekste `z`, `s` yra priimtini konvenciškai, tačiau `for r in rows` ir `with Session(...) as s` pernelyg trumpi. Siūloma: `r` → `row`, `s` (seed.py) → `session`.

---

### 1.3 Trumpos funkcijos, kiekviena daro vieną dalyką

✅ **Atitinka**

- Dauguma metodų ≤ 15 eilučių.
- `_process_entry` (`parking_allocation.py:53–84`) – 32 eilutės. Galima išskirti validacijos bloką į `_validate_entry(event)`, bet šiuo metu dar priimtina.
- `_assign_spot` (`parking_allocation.py:88–106`) – 19 eilučių, daro aiškiai vieną dalyką.

---

### 1.4 Viena atsakomybė klasei

✅ **Atitinka**

| Klasė | Atsakomybė (vienas sakinys) |
|---|---|
| `ParkingAllocationService` | Apdoroja stovėjimo aikštelės įvykius (ENTRY/EXIT) ir grąžina rezultatą |
| `InMemoryRepository` | Saugo ir atnaujina stovėjimo duomenis atmintyje |
| `PostgreSQLRepository` | Saugo ir atnaujina stovėjimo duomenis PostgreSQL duomenų bazėje |
| `SpotEligibilityRule` + poklasiai | Nustato, ar transporto priemonė tinkama konkrečiam vietai |

---

### 1.5 Jokių paslėptų šalutinių efektų

✅ **Atitinka**

- Visi `get_*` metodai tik skaito – nekeičia būsenos.
- `claim_spot`, `mark_spot_free`, `save_active_parking`, `remove_active_parking` – komandos, šalutinis efektas tikėtinas ir pavadinime atspindėtas.

---

### 1.6 Komentarai

⚠️ **Yra perteklinių komentarų**

**Pertekliniai sekciniai komentarai** – metodų pavadinimai jau paaiškina skyrių:

| Failas | Eilutė | Komentaras |
|---|---|---|
| `postgres.py` | 14 | `# --- zone queries ---` |
| `postgres.py` | 29 | `# --- spot queries ---` |
| `postgres.py` | 71 | `# --- active parking queries ---` |
| `parking_allocation.py` | 33 | `# --- exit ---` |
| `parking_allocation.py` | 51 | `# --- entry ---` |
| `parking_allocation.py` | 86 | `# --- spot selection (rules 3 and 4) ---` |

**Geri komentarai (palikti):**
- `postgres.py:96`: `# --- tenant-scoped query builders (every query goes through these) ---` – paaiškina KODĖL, ne KĄ ✅
- `base.py:27`: `"""Lock row, mark as occupied. Returns False if already occupied."""` – dokumentuoja svarbu elgesį ✅
- `postgres.py:42,50`: `# noqa: E712` – būtinas SQLAlchemy boolean ✅

**Siūlomas pataisymas:** ištrinti 6 sekcinius komentarus iš `postgres.py` ir `parking_allocation.py`.

---

### 1.7 Magiški skaičiai ir tekstinės reikšmės

⚠️ **Yra problemų**

| Failas | Eilutė | Magiška reikšmė | Siūlymas |
|---|---|---|---|
| `db/orm_models.py` | 13, 25, 40, 55 | `String(100)`, `String(200)`, `String(50)`, `String(20)` | konstantos `TENANT_ID_LEN = 100` ir t.t. |
| `dependencies.py` | 27 | `status_code=404` | `from fastapi import status; status.HTTP_404_NOT_FOUND` |

---

### 1.8 Kodo dubliavimas

⚠️ **Yra problemų**

**1. `count_free_spots` PostgreSQL implementacijoje** (`postgres.py:46–52`):

```python
def count_free_spots(self, zone_id: str) -> int:
    rows = self._session.execute(
        self._spot_q()
        .where(SpotORM.zone_id == zone_id)
        .where(SpotORM.is_occupied == False)  # noqa: E712
    ).scalars().all()
    return len(rows)
```

Tai tiksliai tas pats filtras kaip `get_free_spots`, tik su `len()`. Siūloma:
```python
def count_free_spots(self, zone_id: str) -> int:
    return len(self.get_free_spots(zone_id))
```
arba naudoti SQL `func.count()` efektyvumui.

**2. Testų konstantos kartojamos trijuose failuose:**

```python
TENANT_A = "biuru-centras-a"   # test_allocation.py:17, test_api.py:13, test_tenant_isolation.py:25
TENANT_B = "prekybos-centras-b"
TS = datetime(2026, 11, 10, 8, 15)  # test_allocation.py:19, test_tenant_isolation.py:27
```

Siūloma: perkelti į `tests/conftest.py`.

**3. Seed duomenys integraciniuose testuose** (`test_api.py:38–49` ir `test_tenant_isolation.py:56–67`): praktiškai identiški blokai. Galima iškelti į `conftest.py` fixture.

---

### 1.9 Nuoseklūs susitarimai

✅ **Atitinka**

- Klaidų apdorojimas nuoseklus: servisas meta `ParkingError`, routes naudoja `HTTPException` – kiekvienam lygiui savas mechanizmas ✅
- SQLAlchemy naudojamas tik `db/` ir `repositories/postgres.py` ✅
- Pydantic tik `api/schemas.py` ✅

---

## 2. Kento Becko paprasto dizaino taisyklės

### 2.1 Visi testai praeina

✅ **Atitinka** – 13/13 unit testai praeina (`pytest tests/test_allocation.py`).

---

### 2.2 Nėra dubliavimo

⚠️ **Yra problemų** – žr. 1.8 skyrių (count_free_spots, testų konstantos).

---

### 2.3 Kodas išreiškia programuotojo ketinimą

✅ **Atitinka iš esmės**

`ELIGIBILITY_RULES` žodynas aiškiai parodo, kuri taisyklė taikoma kiekvienam vietų tipui. `_nearest`, `_select_best`, `_find_best_spot_globally` – gerai pavadinti.

⚠️ **Viena pavojinga vieta** – `parking_allocation.py:71–72`:
```python
while not self._repository.claim_spot(spot.spot_id):
    spot, is_alternative = self._assign_spot(vehicle, event.preferred_zone)
```
Teoriškai, jei kiekvienas naujas `_assign_spot` grąžina tą patį vienintelį laisvą spotą ir jis nuolat „pagrobiamas" kitų gijų, šis ciklas gali kilpoti ilgai. Praktikoje tai retai galima, bet nėra apsaugos (pvz., max iteracijų skaičius). Ketinimas aiškus, rizika maža, bet verta žinoti.

---

### 2.4 Minimalus klasių ir metodų skaičius (YAGNI / KISS)

⚠️ **Maža problema**

`StandardRule`, `EVRule`, `DisabledRule` yra trys atskiros klasės, kiekvienoje – viena eilutė logikos. Strategy šablonas yra pagrįstas, jei taisyklės augs, bet šiuo metu jos trivialios. Jei taisyklės neaugs, galima buvo naudoti paprastus `bool` tikrinimus arba vienos funkcijos žodyną. Tai ribinis YAGNI klausimas – jei planuojama plėtra, šablonas pateisinamas.

`ParkingEvent` dataclass nešioja `tenant_id` ir `timestamp` laukus, bet `ParkingAllocationService.process_event` nei vieno jų nenaudoja. Tai rodo, kad `ParkingEvent` „per daug žino" apie infrastruktūros kontekstą.

---

## 3. OOP koncepcijos ir metrikos

### 3.1 Abstrakcija ir inkapsuliacija

⚠️ **Yra silpnos inkapsuliacija viena vieta**

`Spot` yra `@dataclass` su viešu `is_occupied: bool`. `InMemoryRepository.claim_spot` tiesiogiai keičia:
```python
spot.is_occupied = True   # in_memory.py:41
```
Tai reiškia, kad domeno objektas mutuojamas tiesiogiai iš saugyklos kodo. Geriau: `Spot` turėtų turėti `occupy()` / `release()` metodus, arba `Spot` turėtų būti immutable (frozen dataclass) ir repozitorija kurtų naują kopiją.

Visa kita vidinė būsena tinkamai apsaugota `_` prefiksu ✅.

---

### 3.2 Coupling (ryšio stiprumas)

⚠️ **Yra problema – routes.py tiesiogiai priklauso nuo konkrečios implementacijos**

`routes.py:11`:
```python
from app.repositories.postgres import PostgreSQLRepository
```

`_make_service` ir `get_occupancy` kuria `PostgreSQLRepository` tiesiogiai. API sluoksnis turėtų matyti tik abstrakciją (`ParkingRepository`), o konkrečios implementacijos pasirinkimas turėtų būti `dependencies.py` atsakomybė.

`ParkingAllocationService` priklauso nuo `ParkingRepository` abstrakcijos ✅ – čia DIP laikomas.

---

### 3.3 Cohesion (sangluda)

✅ **Atitinka**

Visi `PostgreSQLRepository` metodai dirba su ta pačia DB sesija ir tais pačiais ORM modeliais. Visi `ParkingAllocationService` metodai dirba su ta pačia repozitorija ir verslo logika.

---

### 3.4 Law of Demeter

✅ **Atitinka iš esmės**

Vienintelė grandinė: `parking_allocation.py:132`:
```python
int(s.spot_id.split("-")[-1])
```
Tai `str` metodų grandinė ant primityvaus lauko – tai priimtina pagal Demeter įstatymą (grandinė ta pati objekto lygyje). Tačiau tai kodifikuoja `spot_id` formatą (`"A-01"`) servise – jei formatas pasikeistų, servisas sugriūtų. Geriau būtų turėti `spot.numeric_suffix()` metodą arba surikiuoti kitaip.

---

### 3.5 Pakankamumas, išbaigtumas, primityvumas

❌ **Yra pažeidimas – `get_all_spots` nėra bazinėje sąsajoje**

`PostgreSQLRepository` turi `get_all_spots` metodą (`postgres.py:30`), kuris **nėra** apibrėžtas `ParkingRepository` abstrakčioje klasėje (`base.py`). Jis naudojamas `routes.py:68`:
```python
for s in repo.get_all_spots(z.zone_id)
```

Tai reiškia:
- Sąsaja yra **neišbaigta** – trūksta metodo
- `routes.py` de facto priklauso nuo konkrečios implementacijos
- `InMemoryRepository` **neturi** `get_all_spots` – jos negalima naudoti `/occupancy` endpoint'e

**Siūlomas pataisymas:** pridėti `get_all_spots` į `ParkingRepository` kaip `@abstractmethod` ir implementuoti `InMemoryRepository`.

---

### 3.6 Composition over inheritance

✅ **Atitinka**

Paveldėjimas naudojamas tik sąsajų implementavimui (`InMemoryRepository(ParkingRepository)`, `PostgreSQLRepository(ParkingRepository)`). Nėra gilių hierarchijų, nėra paveldėjimo kodo pakartotiniam panaudojimui. `SpotEligibilityRule` poklasiai taip pat plokšti.

---

## 4. SOLID principai

### 4.1 SRP – Single Responsibility Principle

⚠️ **Yra maža problema**

`routes.py:get_occupancy` (`routes.py:47–73`) tiesiogiai kuria `PostgreSQLRepository` ir kviečia `repo.get_all_spots` be jokio service sluoksnio. Tai reiškia, kad routes funkcija atlieka tiek HTTP apdorojimą, tiek repozitorijos valdymą. Turėtų būti atskiras servisas (pvz., `ParkingQueryService`) arba bent jau skaitymo operacijos turėtų eiti per abstrakciją.

`ParkingAllocationService` atitinka SRP ✅.

---

### 4.2 OCP – Open/Closed Principle

✅ **Atitinka**

`ELIGIBILITY_RULES` žodynas (`rules.py:26–30`) leidžia pridėti naują vietų tipą ir taisyklę **nekečiant** `_select_best` metodo – tiesiog pridedamas naujas įrašas į žodyną ir nauja klasė. Tai teisingas OCP taikymas.

Naują `SpotType` reikia pridėti į enum – tai priimtinas pažeidimas (enum plėtimas yra pridėjimas, ne keitimas).

---

### 4.3 LSP – Liskov Substitution Principle

⚠️ **Yra pažeidimas**

`InMemoryRepository` ir `PostgreSQLRepository` negali pilnai pakeisti viena kitos, nes `PostgreSQLRepository` turi `get_all_spots` metodą, kurio `InMemoryRepository` neturi. Naudojant `InMemoryRepository` `/occupancy` endpoint'e gautume `AttributeError`.

Nėra `isinstance` tikrinimų ✅ – tai gerai.

---

### 4.4 ISP – Interface Segregation Principle

✅ **Atitinka iš esmės**

`ParkingRepository` sąsaja yra pagrįstai kompaktiška – visi 9 metodai naudojami `ParkingAllocationService`. Nėra metodų, kuriuos implementuojanti klasė priverstų realizuoti nenaudojamus dalykus.

⚠️ **Tačiau** trūksta `get_all_spots` sąsajoje (žr. 3.5). Jei jis būtų pridėtas, visos implementacijos privalėtų jį realizuoti – tai logiška (galima turėti paprastą default implementaciją `InMemoryRepository`).

---

### 4.5 DIP – Dependency Inversion Principle

⚠️ **Yra pažeidimas routes.py lygyje**

`ParkingAllocationService` priklauso nuo abstrakcijos `ParkingRepository` ✅ – čia DIP laikomas puikiai.

`routes.py` pažeidžia DIP dvejopai:
1. `from app.repositories.postgres import PostgreSQLRepository` – importas konkrečios implementacijos
2. `repo = PostgreSQLRepository(tenant_id, session)` `get_occupancy` funkcijoje – tiesioginis kūrimas

**Siūlomas pataisymas:** `dependencies.py` turėtų eksponuoti `get_repository(tenant_id, session) -> ParkingRepository` funkciją, kurią `routes.py` gautų per `Depends(...)`.

---

## 5. Projektavimo šablonai

### Naudojami šablonai

| Šablonas | Kur naudojamas | Vertinimas |
|---|---|---|
| **Repository** | `ParkingRepository` (base.py) + dvi implementacijos | ✅ Teisingai taikytas |
| **Strategy** | `SpotEligibilityRule` + `ELIGIBILITY_RULES` žodynas (rules.py) | ✅ Elegantiškas |
| **Dependency Injection** | `ParkingAllocationService.__init__(repository)` | ✅ Teisingai per konstruktorių |
| **Factory Function** | `_make_service(tenant_id, session)` routes.py:17 | ⚠️ Hard-coded prie konkrečios klasės |

### Kur šablonas aiškiai padėtų

**Factory per `dependencies.py`:**  
`_make_service` ir `PostgreSQLRepository` kūrimas `get_occupancy` galėtų tapti vienu `Depends(get_repository)` – tai užbaigtų DIP ir sumažintų duplikavimą.

**Unit of Work:**  
`get_db()` (dependencies.py:9–16) ir panašus kodas `test_api.py:52–59` iš esmės implementuoja Unit of Work šabloną (commit on success, rollback on failure), bet tai yra ad hoc. Jei projektas augtų, galima būtų iškelti į formalią klasę, tačiau šiuo metu tai būtų over-engineering.

### Anti-patternai

✅ **Nėra** God class, Spaghetti code, Golden hammer.

---

## 6. Testai

### 6.1 Arrange–Act–Assert struktūra

✅ **Atitinka** – visi testai aiškiai turi visas tris fazes.

---

### 6.2 Vienas dalykas per testą, aiškūs pavadinimai

✅ **Atitinka iš esmės**

Testų pavadinimai yra aprašomieji: `test_standard_car_assigned_nearest_standard_spot`, `test_exit_without_entry_rejected_and_counts_unchanged` ✅

⚠️ `test_successful_exit_releases_spot_and_increments_free_count` (`test_allocation.py:266–284`) turi **6 assert'us** – tai per daug vienam testui. Galima išskirti į du: vieną tikrina `result` reikšmes, kitą – repozitorijos būseną po išvažiavimo.

---

### 6.3 Unit testai greiti, nepriklausomi nuo datos/laiko

✅ **Atitinka**

- `TS = datetime(2026, 11, 10, 8, 15)` – fiksuotas timestamp ✅
- Unit testai naudoja `InMemoryRepository`, veikia < 0.02s ✅
- Nėra `datetime.now()` testuose ✅

---

### 6.4 Integraciniai testai aiškiai atskirti

✅ **Atitinka**

`test_tenant_isolation.py` ir `test_api.py` reikalauja `TEST_DATABASE_URL` – jei nėra, `pytest.fail()` su aiškiu pranešimu. Failų pavadinimai aiškiai rodo paskirtį.

⚠️ **Trūksta pytest markers:** nėra `pytest.ini` arba `pyproject.toml` su `@pytest.mark.integration` žymėmis. Tai reiškia, kad `pytest` be `TEST_DATABASE_URL` kviečiant visus testus gaus `FAILED` vietoj `SKIPPED`. Siūloma pridėti `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = ["integration: requires running PostgreSQL database"]
```

---

### 6.5 Priklausomybių injekcija ir imitacijos

✅ **Atitinka**

- Unit testai naudoja `InMemoryRepository` – tikras objektas, ne mock ✅
- `test_api.py` naudoja `app.dependency_overrides[get_db]` – teisingai ✅
- Nėra `unittest.mock` ar sudėtingų statinių metodų imitavimų ✅

---

### 6.6 Ribiniai atvejai, klaidos, tušti duomenys

⚠️ **Trūksta vieno ribinio atvejo**

| Atvejis | Testuojamas? |
|---|---|
| Pilna aikštelė (LOT_FULL) | ✅ `test_full_lot_entry_rejected...` |
| Dublikatas (DUPLICATE_ENTRY) | ✅ `test_duplicate_entry_rejected...` |
| Nėra aktyvaus įvažiavimo (NO_ACTIVE_ENTRY) | ✅ `test_exit_without_entry...` |
| EV automobilis be EV vietų (fallback) | ✅ `test_ev_car_falls_back_to_standard...` |
| Nežinoma zona (UNKNOWN_ZONE) | ❌ **nėra unit testo** |
| Lygus atstumas, numerinis rikiavimas | ✅ du testai |
| Be pageidaujamos zonos (`preferred_zone=None`) | ✅ |

**Siūlomas pataisymas:** pridėti testą į `test_allocation.py`:
```python
def test_unknown_zone_rejected():
    zones = [Zone(zone_id="A", priority=1)]
    spots = [Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10)]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)
    result = service.process_event(entry("LTA123", preferred_zone="NERA"))
    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.UNKNOWN_ZONE
```

---

### 6.7 Testai tikrina tik „negrąžino klaidos"

✅ **Atitinka** – visi testai tikrina konkrečias reikšmes, ne tik statuso kodus.

---

## 7. Architektūra

### 7.1 Verslo logika atskirta nuo API ir saugyklos

⚠️ **Yra vienas pažeidimas**

`routes.py:get_occupancy` kviečia `repo.count_free_spots` ir `repo.get_all_spots` tiesiogiai be jokio service sluoksnio. Verslo logika (ką grąžinti `/occupancy` endpoint'e) turėtų eiti per servisą.

`routes.py:handle_event` – `datetime.now()` iškvietimas routes lygyje yra nedidelė logikos „nuotėkis". Idealu: timestamp turėtų ateiti iš išorės (testuojamumo dėlei), bet praktiškai tai nedidelis kompromisas.

`domain/` neturi jokių FastAPI ar SQLAlchemy importų ✅ – tai labai gerai.

---

### 7.2 Priklausomybių kryptis

⚠️ **Yra vienas pažeidimas**

Teisinga kryptis:
```
api → services → domain
repositories → domain
db (ORM) → domain (per konversiją)
```

Faktinė kryptis:
```
api → services → domain           ✅
api → repositories/postgres        ❌ (routes.py tiesiogiai importuoja PostgreSQLRepository)
repositories/postgres → db/orm_models → domain  ✅
domain → (nieko iš infrastruktūros) ✅
```

`routes.py:11`: `from app.repositories.postgres import PostgreSQLRepository` yra vienintelis pažeidimas. API sluoksnis neturėtų žinoti apie konkrečią saugyklos implementaciją.

---

## Prioritetinis sąrašas

### ❗ Būtina pataisyti (klaidos, kurios pažeidžia architektūros principus)

1. **`get_all_spots` nėra `ParkingRepository` sąsajoje** (`base.py`) – tai LSP pažeidimas ir neišbaigta sąsaja. Pridėti `@abstractmethod get_all_spots` ir implementuoti `InMemoryRepository`. **Failai:** `base.py`, `in_memory.py`

2. **`routes.py` tiesiogiai importuoja `PostgreSQLRepository`** – DIP pažeidimas. Perkelti repozitorijos kūrimą į `dependencies.py` kaip `Depends(get_repository)`. **Failas:** `routes.py`, `dependencies.py`

3. **`count_free_spots` dubliuoja `get_free_spots` filtrą** (`postgres.py:46–52`) – kodo dubliavimas, kuris gali sukelti neatitikimus. **Failas:** `postgres.py`

4. **Trūksta `UNKNOWN_ZONE` unit testo** – nepadengtas `ErrorCode`. **Failas:** `tests/test_allocation.py`

---

### 👍 Būtų gerai pataisyti (kokybė, skaitomumas)

5. **Pridėti `ruff`** į `requirements.txt` ir sukonfigūruoti `pyproject.toml` – automatinis formatavimo ir kokybės tikrinimas.

6. **Sekciniai komentarai** `postgres.py` ir `parking_allocation.py` (6 vnt.) – ištrinti perteklinius `# --- ... ---` komentarus.

7. **Testų konstantos** (`TENANT_A`, `TENANT_B`, `TS`) kartojamos trijuose failuose – perkelti į `conftest.py`.

8. **pytest markers** – pridėti `pyproject.toml` su `integration` žyma, kad integraciniai testai galėtų būti praleisti be DB.

9. **`String(100)` ir panašūs magiški skaičiai** `db/orm_models.py` – iškelti į konstantas.

10. **`for r in rows`** (`postgres.py`) → `for row in rows`; `with Session(engine) as s` (`seed.py`) → `session`.

11. **`spot_id.split("-")[-1]`** (`parking_allocation.py:132`) – `Spot` arba domenas turėtų turėti metodą/logiką, o ne servisas koduoti formato detalę.

---

### ✋ Nekeisti (ir kodėl)

12. **`StandardRule`, `EVRule`, `DisabledRule` kaip atskiros klasės** – Strategy šablonas yra pagrįstas, nes `SpotEligibilityRule` yra aiškiai apibrėžta abstrakcija. Taisyklės greičiausiai augs (pvz., laiko langai, narystė). Tai nėra over-engineering.

13. **`while not self._repository.claim_spot(spot.spot_id):`** – pesimistinė blokavimo strategija (`SELECT ... FOR UPDATE`) yra teisinga konkurencijos valdymui. Ciklas negali suktis be galo: kiekvienas apsisukimas arba sėkmingai užima vietą, arba `_assign_spot` meta `LOT_FULL` (nes laisvos vietos tik mažėja po kiekvieno kito commit). Nekeisti.

14. **`ParkingError` išimčių mechanizmas** – servisas meta tipines išimtis, routes'ai jas fiksuoja – tai švarus ir lengvai testuojamas šablonas. Nekeisti.

15. **`_zone_q()`, `_spot_q()`, `_parking_q()` query builder metodai** (`postgres.py`) – puikus tenant izoliacijos mechanizmas, neleidžiantis „pamiršti" tenant filtro. Nekeisti.

16. **Fiksuotas `TS = datetime(2026, 11, 10, 8, 15)` testuose** – teisingas sprendimas (naudoti `datetime.now()` testuose sukurtų nestabilius testus). Nekeisti.
