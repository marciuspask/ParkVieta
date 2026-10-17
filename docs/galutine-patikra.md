# Galutinė II etapo patikra

Patikros data: 2026-10-17. Dirbta **laikinajame klone** (`/tmp/parkvieta-audit-WLTu/ParkVieta`), gautu iš `git clone https://github.com/marciuspask/ParkVieta.git`. Pagrindinio projekto aplanko nekeista.

---

## A. Paleidimas nuo nulio

### A1. Klonavo iš GitHub

**Komanda:**
```
git remote get-url origin
→ https://github.com/marciuspask/ParkVieta.git
git clone https://github.com/marciuspask/ParkVieta.git /tmp/parkvieta-audit-WLTu/ParkVieta
```
✅ Klonavimas pavyko be klaidų.

### A2. README žingsniai – pastebėtos neatitikties

✅ `.env.example` egzistuoja, `cp .env.example .env` veikia, `DATABASE_URL` ir `TEST_DATABASE_URL` aprašyti.

⚠️ **README demonstravimo žingsnis 1 – netikslus `free_in_zone`:** README teigia, kad po LTA123 įvažiavimo `free_in_zone` bus `2`. Tikras atsakymas:
```json
{"status":"ASSIGNED","zone":"A","spot":"A-01","spot_type":"STANDARD","free_in_zone":5,...}
```
Zonoje A yra 6 vietos (3 STANDARD + 2 EV + 1 DISABLED). Po vieno STANDARD priskyrimo lieka 5 laisvos. README pavyzdys rašytas tarsi zonoje A būtų tik 3 STANDARD vietos.

⚠️ **README atsakymų pavyzdžiai neturi `error_code` ir `message` laukų.** Tikri atsakymai visada grąžina šiuos laukus (pvz., `"error_code": null`), nes servisas grąžina visą `AllocationResult` dataclass kaip `asdict()`. Tai nesukelia klaidos, bet README pavyzdžiai neatspindi tikros išvesties.

✅ Kitos README instrukcijos (paleidimas, testai, ruff, curl scenarijai) tikslios.

### A3. Viena paleidimo komanda

✅ `docker compose up` paleidžia DB, sukuria lenteles, įkelia seed duomenis, paleidžia API. Pasiekiama `http://localhost:8000`.

**Įrodymas:**
```
curl http://localhost:8000/occupancy -H "X-Tenant-ID: biuru-centras-a"
→ 200 OK, tenant biuru-centras-a, 2 zonos, 10 vietų
```

### A4. Testų rezultatai

**Unit testai** (`-m unit`):
```
16 passed, 7 deselected, 1 warning in 1.66s
```
✅ Visi 16 praeina, 0 skipped.

**Integraciniai testai** (`-m integration`):
```
7 passed, 16 deselected, 1 warning in 2.80s
```
✅ Visi 7 praeina, 0 skipped.

**Visi testai:**
```
23 passed, 1 warning in 0.48s
```
✅ Iš viso 23 passed, 0 failed, 0 skipped.

⚠️ **Pastovus įspėjimas visose paleidimo sesijose:**
```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```
Nėra kodo klaida (httpx 0.28.x ir FastAPI 0.136.x sąveika), bet gali kelti klausimų atsiskaitymo metu.

### A5. Linterio patikrinimas

```
ruff check .        → All checks passed!
ruff format --check . → 25 files already formatted
```
✅ Nėra jokių ruff klaidų.

### A6. API demonstravimo scenarijai

| Scenarijus | Laukiamas | Gautas | Sutampa? |
|---|---|---|---|
| 1. LTA123 → STANDARD zona A | `ASSIGNED`, `A-01`, `alternative_zone:false` | `ASSIGNED`, `A-01`, `alternative_zone:false` | ✅ (tik `free_in_zone` skiriasi: 2 vs 5, žr. A2) |
| 2. Pilna STANDARD zona A → DEF001 į B | `ASSIGNED`, `B-01`, `alternative_zone:true` | `ASSIGNED`, `B-01`, `alternative_zone:true` | ✅ |
| 3. EXIT be įvažiavimo ZZZ999 | `REJECTED`, `NO_ACTIVE_ENTRY` | `REJECTED`, `NO_ACTIVE_ENTRY` | ✅ |
| 4. Klientas B bando išvažiuoti kl. A automobilį LTA123 | `REJECTED`, `NO_ACTIVE_ENTRY` | `REJECTED`, `NO_ACTIVE_ENTRY` | ✅ |
| 5. Nežinomas klientas → 404 | `404` | `404` | ✅ |

### A7. Valymas

✅ Konteinieriai sustabdyti (`docker compose down -v`), laikini aplankai ištrinti.

---

## B. II užduoties reikalavimai

### B1. Pagrindinė funkcija (1,5 b.)

✅ **Visas scenarijus**: ENTRY → vietos parinkimas → ASSIGNED; EXIT → atlaisvinimas → RELEASED. Abu keliai veikia.

✅ **Verslo taisyklės**: EV pirmenybė, DISABLED pirmenybė, STANDARD bet kam, fallback į kitą zoną, numerinis ties nuotolio lygybe.

✅ **Klaidų apdorojimas**: DUPLICATE_ENTRY, NO_ACTIVE_ENTRY, UNKNOWN_ZONE, LOT_FULL – visi atmetami, būsena nekeičiama.

✅ **Ne vien CRUD**: servisas `ParkingAllocationService` turi algoritminę vietos parinkimo logiką (`_assign_spot`, `_select_best`, `_nearest`), taisyklių sistemą (`ELIGIBILITY_RULES`), lygiagretumo saugiklį (`claim_spot` su `FOR UPDATE`).

**Tikėtinas balas: 1,5/1,5**

### B2. Kodo struktūra ir kokybė (1 b.)

✅ **Logika atskirta nuo sąsajos**: `ParkingAllocationService` (`app/services/`) nepriklauso nuo FastAPI – nėra nė vieno `fastapi` importo; servisas matytas iš `app/api/routes.py:22`.

✅ **Logika atskirta nuo saugojimo**: servisas dirba tik su `ParkingRepository` ABC; nei `sqlalchemy`, nei `psycopg2` importų servise ar domene.

✅ **Aiškios atsakomybės**: `models.py` – duomenų struktūros; `rules.py` – atitikties taisyklės; `parking_allocation.py` – algoritmas; `postgres.py` – DB prieiga; `routes.py` – HTTP sąsaja.

✅ **Aiškūs pavadinimai**: veiksmažodžiai metodams (`process_event`, `claim_spot`, `mark_spot_free`), daiktavardžiai klasėms (`ParkingAllocationService`, `PostgreSQLRepository`), domeno žodynas viso projekto mastu.

✅ **Dubliavimo nėra**: `_select_best` ir `_nearest` iškelti į atskirus metodus; `_zone_q`/`_spot_q`/`_parking_q` – vienas tenant filtras visoms užklausoms.

**Tikėtinas balas: 1,0/1,0**

### B3. Automatiniai testai (0,5 b.)

✅ **Pagrindinio modulio testai (≥3)**: 16 unit testų `test_allocation.py`:
- Įprastas atvejis: `test_standard_car_assigned_nearest_standard_spot`
- Ribinis/konfliktinis: `test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot`, `test_full_lot_entry_rejected_and_counts_unchanged`, `test_duplicate_entry_rejected_car_stays_at_original_spot`, `test_equal_distance_numeric_order_not_lexicographic`
- Klaidos: `test_exit_without_entry_rejected_and_counts_unchanged`, `test_unknown_zone_entry_rejected_and_counts_unchanged`

✅ **Izoliacijos testas**: `test_tenant_b_cannot_exit_car_parked_under_tenant_a` (`test_allocation.py:145`) naudoja du atskirus `InMemoryRepository` su skirtingais klientais.

✅ **Tikrinami konkretūs rezultatai**: kiekvienas testas tikrina `status`, `spot`, `error_code` ir/arba `free_in_zone` konkrečiomis reikšmėmis.

**Tikėtinas balas: 0,5/0,5**

### B4. Klientų duomenų atskyrimas (0,5 b.)

✅ **Du klientai**: `biuru-centras-a` ir `prekybos-centras-b` seed duomenyse.

✅ **Kiekvienas saugyklos metodas per tenant filtrą**: visi trys query builder metodai `_zone_q`, `_spot_q`, `_parking_q` (`postgres.py:89-95`) filtruoja `WHERE tenant_id = self._tenant_id`. Nėra jokio metodo, kuris praleistų tenant filtrą.

✅ **Kiekvienas API maršrutas**: `get_tenant_id` tikrina klientą DB; `get_repository` sukuria `PostgreSQLRepository` su to kliento `tenant_id`. Abi `GET /occupancy` ir `POST /events` naudoja `Depends(get_tenant_id)`.

✅ **Vienas klientas negali keisti kito duomenų**: `test_tenant_b_exit_rejected_and_tenant_a_data_unchanged` įrodo per integracinius testus; `test_exit_tenant_a_car_rejected_in_tenant_b_context` įrodo per API TestClient testus.

**Tikėtinas balas: 0,5/0,5**

### B5. Paleidimas ir README (0,5 b.)

✅ **Įrankiai ir versijos**: README lentelė atitinka `requirements.txt` (FastAPI 0.136.3, SQLAlchemy 2.0.50 ir kt.) ir `Dockerfile` (`python:3.12-slim`).

✅ **Konfigūracija**: `.env.example` be tikrų raktų (visi `password` – demonstraciniai), `DATABASE_URL` ir `TEST_DATABASE_URL` aprašyti.

✅ **Paleidimo komanda**: `docker compose up` – viena komanda.

✅ **Testų komandos**: visos trys (`-m unit`, `-m integration`, visos) aprašytos su tikėtamu rezultatu (`21 passed` – kiek pasenęs, nes dabar 23).

⚠️ **Tikėtinas testų skaičius README neaktualus**: README rašo „Tikėtinas rezultatas: 21 passed", bet faktiškai yra 23 (pridėti 2 testai vėliau). Nedidelė neatitiktis.

✅ **Pavyzdiniai duomenys**: abu klientai su visomis vietomis aprašyti lentelėmis.

✅ **Demonstravimo žingsniai**: visi 5 scenarijai aprašyti su curl komandomis (žr. A6 – visi veikia).

**Tikėtinas balas: 0,45/0,5** (mažas atskaičiavimas už `free_in_zone` ir testų skaičiaus neatitiktis README)

---

## C. Atitiktis projektavimo dokumentui

### C1. 3 skyriaus taisyklės 1–5

| Taisyklė | Kodo vieta | Testas |
|---|---|---|
| 1. Validacija (DUPLICATE, NO_ENTRY, UNKNOWN_ZONE) | `parking_allocation.py:36-72` | `test_exit_without_entry_rejected_and_counts_unchanged`, `test_duplicate_entry_rejected_car_stays_at_original_spot`, `test_unknown_zone_entry_rejected_and_counts_unchanged` |
| 2. Tipo atitiktis (EV→EV, DISABLED→DISABLED, STANDARD→visiems) | `rules.py:10-25`, `parking_allocation.py:121-133` | `test_ev_car_prefers_ev_spot_over_nearer_standard_spot`, `test_ev_car_falls_back_to_standard_when_no_ev_spots`, `test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot` |
| 3. Geriausios vietos parinkimas (atstumas, tada numeris) | `parking_allocation.py:134-140` (`_nearest`) | `test_equal_distance_assigns_spot_with_lower_number`, `test_equal_distance_numeric_order_not_lexicographic`, `test_standard_car_assigned_nearest_standard_spot` |
| 4. Pilnos zonos konfliktas (kita zona pagal prioritetą) | `parking_allocation.py:92-111` (`_assign_spot`) | `test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot` + integraciniai |
| 5. Užimtumo invariantas (skaičius nepakinta atmetus) | `parking_allocation.py:22-35` (klaidos grąžina tiesiai) | `test_exit_without_entry_rejected_and_counts_unchanged`, `test_full_lot_entry_rejected_and_counts_unchanged` |

✅ Visos 5 taisyklės įgyvendintos ir turi testus.

### C2. Scenarijų lentelės atitikimas testams

| Scenarijus iš dokumento | Testas | Tie patys duomenys? |
|---|---|---|
| Įprastas: LTA123, A zonoje A-01 (10m), A-02 (25m), A-03 (40m) → A-01, 2 laisvos | `test_standard_car_assigned_nearest_standard_spot` | ✅ (tie patys duomenys ir rezultatas) |
| Ribinis: A zonoje tik A-05 EV, B zonoje B-01 STANDARD, KLB456 → B-01, alternative_zone:true | `test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot` | ✅ |
| Klaida: MNC789 EXIT be įvažiavimo → REJECTED, NO_ACTIVE_ENTRY | `test_exit_without_entry_rejected_and_counts_unchanged` | ✅ |
| Klaida pilna: visos vietos užimtos → REJECTED, LOT_FULL | `test_full_lot_entry_rejected_and_counts_unchanged` | ✅ |
| Dublikatas: LTA123 jau A-01 → REJECTED, DUPLICATE_ENTRY | `test_duplicate_entry_rejected_car_stays_at_original_spot` | ✅ |
| Izoliacija: kl. B EXIT kl. A automobilio → REJECTED, duomenys nepakinta | `test_tenant_b_cannot_exit_car_parked_under_tenant_a` | ✅ |

✅ Visi 6 scenarijai turi testus su tais pačiais duomenimis.

### C3. Nukrypimai nuo dokumento (docs/pakeitimai-nuo-1-etapo.md)

Dokumente aprašyti 3 nukrypimai:
1. `preferred_zone: None` → globaliai arčiausia vieta
2. `RELEASED` vietoj `ASSIGNED` išvažiavimui
3. `tenants` lentelė DB, nežinomas klientas → 404

✅ Visi trys nukrypimai aprašyti su priežastimis ir testų nuorodomis.

✅ **Neaprašytų nukrypimų nerastas**: kiti pakeitimai (lygybės sprendimas numeriu, `_select_best` refaktoringas, lygiagretumo testas) yra impl. detalės, ne taisyklių pakeitimai.

### C4. STAFF_ONLY tipo pridėjimas (4 skyriaus palaikomumas)

Dabartinė struktūra:
- `SpotType` enum – `app/domain/models.py:17-21`
- `SpotEligibilityRule` ABC – `app/domain/rules.py:5-8`
- `ELIGIBILITY_RULES` dict – `app/domain/rules.py:27-31`

**Norint pridėti `STAFF_ONLY` reiktų keisti:**
1. `app/domain/models.py` – `SpotType` enum: `STAFF_ONLY = "STAFF_ONLY"` (1 eilutė)
2. `app/domain/rules.py` – nauja klasė `StaffOnlyRule(SpotEligibilityRule)` + įrašas `ELIGIBILITY_RULES` žodyne (~5 eilutės)
3. `db/seed.py` – pavyzdiniai duomenys su `STAFF_ONLY` vietomis (nebūtina kodo pasikeitimui)

**Nekeičiami failai:** `parking_allocation.py`, `postgres.py`, `in_memory.py`, `routes.py`, visi esami testai.

✅ OCP laikomas: servisas naudoja `ELIGIBILITY_RULES[s.spot_type]` generiškai; pridėjus naują tipą algoritmas nepakinta.

---

## D. Paskaitų reikalavimai

### D1. Švarus kodas

✅ **Formatavimas**: `ruff format --check` – 25 files already formatted.

✅ **Pavadinimai**: veiksmažodžiai funkcijoms (`process_event`, `claim_spot`, `get_free_spots`), daiktavardžiai klasėms (`Vehicle`, `ParkingAllocationService`, `PostgreSQLRepository`), domeno žodynas (tenant, spot, zone, plate – ne user, item, resource).

✅ **Trumpos funkcijos**: ilgiausia `_process_entry` – ~20 eilučių; `_assign_spot` – ~19 eilučių; visi kiti metodai ≤10 eilučių.

✅ **Viena atsakomybė**: kiekvienas metodas atlieka vieną veiksmą (pvz., `_nearest` tik randa artimiausią, `count_free_spots` tik skaičiuoja).

✅ **Paslėptų šalutinių efektų nėra**: `_find_best_spot` tik skaito, nekeičia būsenos; visi state pakeitimai – tik `claim_spot`, `mark_spot_free`, `save_active_parking`, `remove_active_parking`.

✅ **Komentarų nedaug**: tik būtini (pvz., `"""Lock row, mark as occupied. Returns False if already occupied."""` `base.py:28`).

✅ **Magiškų skaičių nėra**: nėra hardcoded konstantų logikoje.

✅ **Dubliavimo nėra**: `_select_best` sujungia tai, kas anksčiau būtų duplikata.

✅ **Nuoseklūs susitarimai**: visas projektas lietuvių kalba (doc eilutės, komentarai), tipo anotacijos visur, klaidų apdorojimas per `ParkingError` → `AllocationResult(REJECTED, ...)`.

### D2. Kento Becko paprasto dizaino taisyklės / KISS / YAGNI

✅ **Testai praeina**: 23/23.

✅ **Intent aiškus**: `_select_best` pavadinimas aiškiai atskleidžia tikslą.

✅ **Dubliavimo nėra** (žr. D1).

✅ **Mažiausias elementų skaičius**: nėra perteklinių abstrakcijų. `ParkingError` – paprasta Exception subklasė, ne hierarchija. `AllocationResult` – dataclass, ne Pydantic modelis.

✅ **KISS**: nėra event bus, nėra CQRS, nėra factory klasių – tik tai, ko reikia.

✅ **YAGNI**: nėra „ateičiai" palikto kodo; `preferred_zone: None` atvejis pridėtas tik kai buvo rastas reali problema.

### D3. OOP metrikos

✅ **Inkapsuliacija**: `_tenant_id`, `_repository`, `_spots`, `_zones`, `_active_parkings` – visi privatūs; viešieji metodai atitinka repozitorijos sąsają.

✅ **Coupling (žemas)**: servisas priklauso tik nuo `ParkingRepository` ABC ir domeninių objektų. API priklauso nuo serviso ir repozitorijos. Domain nepriklauso nuo nieko išorinio.

✅ **Cohesion (aukšta)**: `ParkingAllocationService` dirba tik su parkavimo paskyrimo logika. `PostgreSQLRepository` dirba tik su DB prieiga.

✅ **Law of Demeter**: servisas kviečia `self._repository.metodas(...)` – nėra grandinės `self._repository.kažkas.metodas()`.

✅ **Pakankamumas ir išbaigtumas**: `ParkingRepository` turi visus reikalingus metodus, bet ne perteklinių.

✅ **Composition over inheritance**: `ParkingAllocationService` naudoja `ParkingRepository` per kompoziciją (konstruktoriaus parametras), ne paveldėjimą.

### D4. SOLID

| Principas | Pavyzdys | Galimi pažeidimai |
|---|---|---|
| **SRP** | `ParkingAllocationService` – tik paskyrimo logika; `PostgreSQLRepository` – tik DB prieiga; `routes.py` – tik HTTP sąsaja | Nėra reikšmingų pažeidimų |
| **OCP** | `ELIGIBILITY_RULES` dict + `SpotEligibilityRule` ABC – naują tipą pridedi nekeitant algoritmo (`rules.py:27-31`) | `SpotType` enum reikia papildyti, bet tai vienos eilutės pakeitimas |
| **LSP** | `InMemoryRepository` ir `PostgreSQLRepository` abi teisingai realizuoja `ParkingRepository` – testai kerta abi realizacijas | Nėra pažeidimų |
| **ISP** | `ParkingRepository` sąsaja – 10 metodų, visi naudojami serviso | Galima diskutuoti, ar `get_all_spots` (tik UI) turėtų būti atskiroje sąsajoje |
| **DIP** | `ParkingAllocationService.__init__(self, repository: ParkingRepository)` – priklauso nuo abstrakcijos, ne `PostgreSQLRepository` | Nėra pažeidimų |

### D5. Projektavimo šablonai

✅ **Strategy** (`rules.py:5-31`): `SpotEligibilityRule` ABC su `StandardRule`, `EVRule`, `DisabledRule` realizacijomis. Pagrįstas: naujus tipus galima pridėti nekaitant algoritmo.

✅ **Repository** (`repositories/base.py`, `postgres.py`, `in_memory.py`): atskiria domeną nuo duomenų saugojimo. Pagrįstas: unit testai naudoja `InMemoryRepository` be DB.

✅ **Dependency Injection** (per konstruktorių ir FastAPI `Depends`): pagrįstas – leidžia keisti realizaciją neliečiant serviso.

**Anti-patternai:**
- ❌ **God class**: nėra – `ParkingAllocationService` (~138 eilučių) neatlieka per daug.
- ❌ **Spaghetti code**: nėra – aiški kodo struktūra.
- ❌ **Golden hammer**: nėra perteklinio šablonų naudojimo.

### D6. Testų kokybė

✅ **Arrange–Act–Assert**: kiekvienas testas aiškiai atskiria duomenis, veiksmą ir tikrinimą. Pavyzdys `test_allocation.py:65-82`.

✅ **Vienas testas – viena elgsena**: `test_equal_distance_assigns_spot_with_lower_number` tikrina tik lygybės sprendimą.

✅ **Aiškūs pavadinimai**: `test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot` – iš pavadinimo aišku, ką tikrina.

✅ **Unit testai atmintyje**: `InMemoryRepository` naudoja Python žodynus – nėra DB, laiko ar eilės priklausomybės.

✅ **Testuose nėra verslo logikos**: testai nusprendžia rezultatą pirmiau (assert), ne skaičiuoja.

✅ **DI ir imitacijos**: `InMemoryRepository` konstruktoriaus parametras leidžia duoti bet kokią pradinę būseną.

✅ **Ribiniai atvejai**: lygus atstumas, nežinoma zona, pilna aikštelė, dublikatas – visi aprašyti.

✅ **Testai nepraeitų be kodo**: žr. D7.

### D7. Testų tikrumas (mutacijos)

#### Mutantas 1: `_parking_q` tenant filtras (`==` → `!=`)

**Pakeitimas:** `postgres.py:95` – `ActiveParkingORM.tenant_id != self._tenant_id`

**Nukritę testai (4):**
```
FAILED tests/test_api.py::test_exit_tenant_a_car_rejected_in_tenant_b_context
FAILED tests/test_tenant_isolation.py::test_tenant_b_cannot_read_tenant_a_active_parking
FAILED tests/test_tenant_isolation.py::test_tenant_b_exit_rejected_and_tenant_a_data_unchanged
FAILED tests/test_tenant_isolation.py::test_tenant_b_entry_uses_own_spot_and_tenant_a_spot_unchanged
```
✅ Testai sugavo klaidą.

#### Mutantas 2: `claim_spot` patikrinimas po užrakinimo (`is_occupied` → `not is_occupied`)

**Pakeitimas:** `postgres.py:41` – `if not row.is_occupied: return False`

**Unit testai**: visi 16 praeina (naudoja `InMemoryRepository` – nepakeitė).

⚠️ **Integraciniai testai**: sukelia **begalinį ciklą** `_process_entry:while not self._repository.claim_spot(...)` (claim_spot visada grąžina False kai vieta laisva) – testai kabo, neduoda aiškaus FAIL.

**Išvada:** Šios svarbios taisyklės pažeidimas nepagaunamas *greitai* (unit testai nepadengia Postgres realizacijos; integraciniai kabo). Tai silpniausia testų vieta – nėra unit testo, kuris tiesiogiai tikrintų `InMemoryRepository.claim_spot` semantiką pakartotinio užrakinimo atveju.

#### Mutantas 3: `EVRule` tipo patikrinimas (pašalintas `vehicle_type == VehicleType.EV`)

**Pakeitimas:** `rules.py:13` – `return spot.spot_type == SpotType.EV`

**Nukritęs testas (1):**
```
FAILED tests/test_allocation.py::test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot
  assert result.spot == "B-01"  # gautas "A-05" (STANDARD auto gavo EV vietą)
```
✅ Testas sugavo klaidą.

### D8. Architektūra

✅ **Priklausomybių kryptis**: `api → services → domain`; `repositories → domain`. Patikrinta importais:
- `domain/` – importuoja tik `dataclasses`, `datetime`, `enum` (standartinė biblioteka).
- `services/` – importuoja tik `domain/` ir `repositories/base.py`.
- `repositories/postgres.py` – importuoja `domain/` ir `db/orm_models.py`.
- `api/routes.py` – importuoja `services/`, `repositories/base.py`, `domain/models.py`.

✅ **Domenas nepriklauso nuo FastAPI/SQLAlchemy**: `grep -rn "import" app/domain/` – tik `dataclasses`, `datetime`, `enum`.

✅ **Transakcijos riba vienoje vietoje**: `get_db()` (`dependencies.py:8-17`) – vienas `try/yield/commit/rollback` blokas vienai užklausai.

---

## E. Repozitorijos higiena

### E1. Nepageidaujami failai git'e

⚠️ **`II-uzduoties-reikalavimai.pdf` stebimas git'e** (git ls-files rezultatas). `.gitignore` nurodo `docs/ii-uzduotis.pdf`, bet ne `II-uzduoties-reikalavimai.pdf` šaknyje. PDF yra sekamas ir bus matomas dėstytojui.

⚠️ **14 `__pycache__` / `.pyc` failų stebimi git'e** (`app/__pycache__/`, `tests/__pycache__/` ir kt.). `.gitignore` turi `__pycache__/`, bet failai jau buvo pridėti anksčiau (gitignore neveikia jau sekamtiems failams).

**Paveikti failai:**
```
II-uzduoties-reikalavimai.pdf
app/__pycache__/__init__.cpython-314.pyc
app/domain/__pycache__/*.pyc  (4 failai)
app/repositories/__pycache__/*.pyc  (3 failai)
app/services/__pycache__/*.pyc  (2 failai)
tests/__pycache__/*.pyc  (4 failai)
```

✅ `.env` nestebimas, `.venv` nestebimas, `docs/ii-uzduotis.pdf` nestebimas.

### E2. Kodo švarumo patikra

✅ **Nėra užkomentuoto kodo**: grepa po `#.*=\|#.*import\|#.*def` nieko nerado reikšmingo.

✅ **Nėra TODO be paaiškinimo**: `grep TODO` rado tik `XXX000` (numerio reikšmė teste, ne komentaras).

✅ **Nenaudojamų failų nėra**: visi failai naudojami.

✅ **Nenaudojamų importų nėra**: `ruff check` patikrina importus – 0 klaidų.

### E3. docs/ai-naudojimas.md

✅ **Visi 7 etapai aprašyti** lentelėje.

✅ **„Ką pakeičiau ir kodėl" stulpelis užpildytas** kiekvienam etapui su konkrečiais pakeitimais (pvz., „Pridėjau patikrinimą po užrakinimo", „Fiksavau bibliotekų versijas").

✅ **Patikrinimai** skyrius aprašo, kaip buvo tikrinamas izoliacijos testų tikrumas.

---

## F. Pasiruošimas atsiskaitymui

### 10 klausimų su atsakymų vieta

| # | Klausimas | Failas ir eilutės |
|---|---|---|
| 1 | Kokiu algoritmu parenkama geriausia vieta, kai atstumas vienodas? | `app/services/parking_allocation.py:134-140` (`_nearest`), `app/domain/models.py:6-10` (`spot_number`) |
| 2 | Kaip užtikrinta, kad du vienalaikiai įvažiavimai negauna tos pačios vietos? | `app/repositories/postgres.py:37-44` (`claim_spot` su `with_for_update()`), `tests/test_tenant_isolation.py:183-219` |
| 3 | Kaip Sistema užtikrina, kad klientas B negali paveikti kliento A duomenų? | `app/repositories/postgres.py:89-95` (`_zone_q`, `_spot_q`, `_parking_q`), `tests/test_tenant_isolation.py:106-134` |
| 4 | Koks projektavimo šablonas naudojamas vietų tipo taisyklėms? Kaip pridėtum naują tipą? | `app/domain/rules.py:5-31`, `app/services/parking_allocation.py:121-133` |
| 5 | Kaip Domain modelis priklauso nuo FastAPI arba SQLAlchemy? (Spoileris: nepriklauso) | `app/domain/models.py:1-3`, `app/domain/rules.py:1-3` – tik stdlib |
| 6 | Koks SOLID principas užtikrina, kad servisas nepriklauso nuo konkrečios DB? | `app/repositories/base.py:1-30` (DIP), `app/services/parking_allocation.py:17-20` |
| 7 | Kaip testai veikia be DB? Kodėl `InMemoryRepository` pakanka unit testams? | `app/repositories/in_memory.py:1-55`, `tests/test_allocation.py:1-30` |
| 8 | Kokią klaidą grąžina sistema, kai automobilis bando išvažiuoti, bet nėra įvažiavęs? | `app/services/parking_allocation.py:36-44`, `app/domain/models.py:35` (`NO_ACTIVE_ENTRY`) |
| 9 | Kaip dirba `init_if_empty`? Kodėl seed paleidžiamas kaskart paleidus Docker? | `db/seed.py:137-145` – tikrina, ar `tenants` lentele tuščia; `Dockerfile:5` – CMD visada vykdo |
| 10 | Kur aprašyti pakeitimai nuo I etapo? Kodėl `RELEASED` vietoj `ASSIGNED`? | `docs/pakeitimai-nuo-1-etapo.md`, `app/domain/models.py:26` |

### 3 nedideli pakeitimai, kurių gali paprašyti dėstytojas

| Pakeitimas | Failai keisti |
|---|---|
| Pridėti `STAFF_ONLY` vietų tipą tik darbuotojams | `app/domain/models.py` (enum), `app/domain/rules.py` (nauja klasė + dict įrašas), `tests/test_allocation.py` (2 nauji testai) |
| Pakeisti `count_free_spots` realizaciją iš `len(get_free_spots(...))` į atskirą SQL `COUNT(*)` užklausą | `app/repositories/postgres.py:23-24` |
| Pridėti `GET /spots/{spot_id}` maršrutą vienos vietos detalėms | `app/api/routes.py`, `app/api/schemas.py` (naujas response modelis) |

---

## Suvestinė lentelė

| Kriterijus | Tikėtinas balas | Kas trūksta |
|---|---|---|
| Pagrindinė funkcija (1,5 b.) | **1,5/1,5** | Nieko |
| Kodo struktūra ir kokybė (1 b.) | **1,0/1,0** | Nieko |
| Automatiniai testai (0,5 b.) | **0,5/0,5** | Nieko |
| Klientų duomenų atskyrimas (0,5 b.) | **0,5/0,5** | Nieko |
| Paleidimas ir README (0,5 b.) | **0,45/0,5** | `free_in_zone` pavyzdyje netikslus; testų skaičius README (21 vs 23) |
| **Iš viso** | **~3,95/4,0** | |

---

## Prioritetinis sąrašas

### Kritiška (gali kainuoti balus)

1. **`__pycache__` ir `II-uzduoties-reikalavimai.pdf` git'e** – repozitorijos higiena, gali sumažinti kodo struktūros balą. Sprendimas: `git rm -r --cached app/__pycache__ tests/__pycache__ II-uzduoties-reikalavimai.pdf`, tada commit.

### Rekomenduojama (padidintų kokybę)

2. **README `free_in_zone: 2` → `5`** demonstravimo žingsnyje 1 – nesutampa su realia sistema, gali suklaidinti dėstytoją tikrinant rankiniu būdu.

3. **README tikėtamas testų skaičius** – pakeisti `21 passed` → `23 passed`.

4. **`claim_spot` mutacijos problema** – nėra unit testo, kuris tikrintų `InMemoryRepository.claim_spot` dvigubo užrakinimo scenarijų. Galima pridėti testą: `claim_spot` po pirmojo `claim_spot` grąžina `False`. Tai nepaveikia esamo funkcionalumo, bet pagerina testų padengimą kritinei taisyklei.

### Kosmetika

5. **`httpx` deprecation warning** – `httpx2` dar neišleistas kaip stabilus paketas; šis įspėjimas yra bibliotekų versijų konfliktas, kurį sunku apeiti. Galima dokumentuoti `docs/ai-naudojimas.md`.

6. **API atsakymas grąžina `"error_code": null, "message": null`** sėkminguose atsakymuose (nes `asdict()` serializuoja visus laukus). Tai ne klaida, bet README pavyzdžiai to nerodo.

---

## G. Pataisyta po patikros

### G1. Repozitorijos higiena

Pašalinti iš git stebėjimo su `git rm --cached`:
- 14 `__pycache__` / `.pyc` failų (`app/`, `tests/` ir jų pakatalogiai).
- `II-uzduoties-reikalavimai.pdf` šakninėje direktorijoje.

`.gitignore` jau turėjo taisyklingas taisykles (`__pycache__/`, `*.pyc`), tačiau failai buvo įtraukti anksčiau – `git rm --cached` pašalino juos iš indekso neprarandant lokalių kopijų.

### G2. README tikri demonstravimo rezultatai

Pataisyti du neatitikimai (žr. A2):
- **`free_in_zone`**: 1 žingsnio pavyzdyje pakeista `2` → `5` (zonoje A yra 6 vietos, po pirmo STANDARD priskyrimo lieka 5 laisvos).
- **Testų skaičius**: pakeista `21 passed` → `24 passed` (dabartinis skaičius).

### G3. Begalinio ciklo apsauga

**Problema (D7 mutantas 2):** `_process_entry` naudojo `while True: claim_spot(...)` be atminties – jei `claim_spot` visada grąžina `False`, ciklas nekada nesibaigia.

**Sprendimas (TDD):**

1. *Raudona:* parašytas testas `test_claim_spot_always_false_returns_lot_full_not_hang` su `signal.alarm(2)` – patvirtino, kad senas kodas kabo.
2. *Žalia:* `_process_entry` papildyta `failed_spot_ids: set[str]` – nepavykusios vietos į sąrašą, `_assign_spot` jų nebepasiūlo; kai visi kandidatai išsemti, meta `ParkingError(LOT_FULL, ...)`.
3. *Refaktorinimas:* `signal.alarm` pakeistas skaičiuojančiu stubu `_NeverClaimsRepository` su konstanta `_MAX_CLAIM_ATTEMPTS = 10` – pašalinta priklausomybė nuo `signal` modulio (veikia ir Windows).

**Mutacinė patikra:** testas tikrina `REJECTED / LOT_FULL` ir `claim_spot_call_count == 1` (lygiai tiek, kiek yra tinkamų vietų) – sugautų mutantų skaičius išaugo.

### G4. Filtro perkėlimas į `_select_best`

`s.spot_id not in excluded_spot_ids` filtras kartojosi `_find_best_spot` ir `_find_best_spot_globally`. Perkeltas į `_select_best(vehicle, spots, excluded_spot_ids)`:

```python
candidates = [s for s in spots if s.spot_id not in excluded_spot_ids]
```

Abu kvietėjai perduoda neapdorotą sąrašą ir `excluded_spot_ids`; filtravimas vyksta vienoje vietoje. Elgsena nepakito – visi 24 testai praeina.

### G5. Kosmetiniai pataisymai

| # | Failas | Pakeitimas |
|---|---|---|
| #1 | `app/api/dependencies.py:29` | HTTP 404 pranešimas `"Tenant '...' not found"` → `"Klientas '...' nerastas"` |
| #2 | `app/repositories/base.py:29` | `claim_spot` docstring anglų → lietuvių |
| #4 | `tests/test_allocation.py` | Maginis skaičius `10` → klasės konstanta `_MAX_CLAIM_ATTEMPTS = 10` |
| #5 | `tests/test_allocation.py`, `tests/test_tenant_isolation.py` | `TS` → `SAMPLE_TIMESTAMP` |
| #7 | `app/services/parking_allocation.py` | Pašalintos 3 skyrių antraštės: `# --- exit ---`, `# --- entry ---`, `# --- spot selection (rules 3 and 4) ---` |
| #8 | `app/repositories/postgres.py` | Pašalintos 4 skyrių antraštės: `# --- zone queries ---`, `# --- spot queries ---`, `# --- active parking queries ---`, `# --- conversion ---` |
| #9 | `tests/test_tenant_isolation.py` | `repo_b_exit(repo_b, plate)` → `exit_vehicle(repo, tenant_id, plate)` |

### G6. Atmesti pasiūlymai

| # | Pasiūlymas | Atmetimo priežastis |
|---|---|---|
| #3 | `claim_spot_call_count` → `_claim_spot_call_count` | Atributas skirtas išoriniam nuskaitymui teste (`assert repo.claim_spot_call_count == 1`); privatus atributas būtų skaitomas iš išorės per `repo._claim_spot_call_count`, kas yra blogesnis stilius nei tiesioginis viešas testuojamas atributas. |
| #6 | `TENANT_A`, `TENANT_B` perkelti į `conftest.py` | Tai domeniniai testų duomenys, ne bendrinama logika; konstantų importas iš `conftest.py` kurtų netiesioginę priklausomybę tarp nesusijusių testų failų ir laikomas bloga praktika. |
