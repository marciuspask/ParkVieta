# ParkVieta

SaaS sistema parkavimo aikštelių valdytojams. Pagal įvažiavimo ir išvažiavimo įvykius skaičiuoja laisvas vietas zonose ir atvykstančiam automobiliui parenka tinkamiausią laisvą vietą pagal vietų tipo ir atstumo taisykles.

## Įrankiai ir versijos

| Įrankis | Versija |
|---------|---------|
| Python | 3.12 |
| FastAPI | 0.136.3 |
| SQLAlchemy | 2.0.50 |
| psycopg2-binary | 2.9.12 |
| Pydantic | 2.13.4 |
| python-dotenv | 1.2.2 |
| pytest | 9.1.1 |
| httpx | 0.28.1 |
| ruff | 0.11.13 |
| PostgreSQL | 16 (Docker image) |
| Docker Compose | 2.x |

## Konfigūracija

```sh
cp .env.example .env
```

`.env` kintamieji:

| Kintamasis | Paskirtis |
|------------|-----------|
| `DATABASE_URL` | Produkcijos DB (naudoja programa ir seed skriptas lokaliai) |
| `TEST_DATABASE_URL` | Testų DB (atskirta nuo produkcijos) |

Testų DB sukuriama automatiškai `docker compose up -d` metu (per `db/init.sql`).

## Paleidimas

```sh
docker compose up
```

Viena komanda:
1. Paleidžia PostgreSQL 16 konteienerį.
2. Sukuria `parkvieta` duomenų bazę ir lenteles.
3. Įkelia pavyzdinius duomenis (tik jei DB tuščia).
4. Paleidžia FastAPI programą.

Programa pasiekiama: **http://localhost:8000**  
Swagger API dokumentacija: **http://localhost:8000/docs**

Pradėti iš naujo nuo tuščios DB:

```sh
docker compose down -v && docker compose up
```

## Kodo kokybė

```sh
ruff check .          # linteris: tikrina kodo kokybę
ruff format --check . # tikrina formatavimą (be pakeitimų)
ruff format .         # pritaiko formatavimą
```

## Testai

Testai suskirstyti į du tipus su pytest markeriais:

| Markeris | Failas | DB reikalinga? |
|----------|--------|----------------|
| `unit` | `tests/test_allocation.py` | Ne |
| `integration` | `tests/test_api.py`, `tests/test_tenant_isolation.py` | Taip |

```sh
# Tik greiti vienetiniai testai (be DB):
python -m pytest -m unit -v

# Tik integraciniai testai (reikia veikiančios DB):
docker compose up -d
python -m pytest -m integration -v

# Visi testai:
docker compose up -d
python -m pytest -v
```

Tikėtinas rezultatas: **23 passed** (16 unit + 7 integration).

## Pavyzdiniai duomenys

Automatiškai sukuriami du klientai:

### Biurų centras A (`X-Tenant-ID: biuru-centras-a`)

| Zona | Prioritetas | Vieta | Tipas | Atstumas |
|------|-------------|-------|-------|----------|
| A | 1 | A-01 | STANDARD | 10 m |
| A | 1 | A-02 | STANDARD | 20 m |
| A | 1 | A-03 | STANDARD | 30 m |
| A | 1 | A-04 | EV | 15 m |
| A | 1 | A-05 | EV | 25 m |
| A | 1 | A-06 | DISABLED | 8 m |
| B | 2 | B-01 | STANDARD | 5 m |
| B | 2 | B-02 | STANDARD | 15 m |
| B | 2 | B-03 | STANDARD | 25 m |
| B | 2 | B-04 | STANDARD | 35 m |

### Prekybos centras B (`X-Tenant-ID: prekybos-centras-b`)

| Zona | Prioritetas | Vieta | Tipas | Atstumas |
|------|-------------|-------|-------|----------|
| A | 1 | A-01 | STANDARD | 12 m |
| A | 1 | A-02 | STANDARD | 20 m |
| A | 1 | A-03 | STANDARD | 28 m |
| A | 1 | A-04 | STANDARD | 36 m |
| A | 1 | A-05 | STANDARD | 44 m |

## Demonstravimo žingsniai

Atidaryti **http://localhost:8000** (vartų imitacijos sąsaja) arba naudoti `curl` komandas žemiau.

### 1. Paprastas automobilis gauna artimiausią STANDARD vietą (klientas A)

Laukiama: `ASSIGNED`, vieta **A-01** (10 m – artimiausia STANDARD vieta). EV vietos lieka laisvos.

```sh
curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: biuru-centras-a" \
  -d '{"event_type":"ENTRY","plate":"LTA123","vehicle_type":"STANDARD","has_disability_permit":false,"preferred_zone":"A"}' \
  | python3 -m json.tool
```

Tikėtinas atsakymas:
```json
{
    "status": "ASSIGNED",
    "zone": "A",
    "spot": "A-01",
    "spot_type": "STANDARD",
    "free_in_zone": 5,
    "alternative_zone": false,
    "error_code": null,
    "message": null
}
```

### 2. Pilna zona A → paprastas automobilis gauna vietą zonoje B

Pirmiausia užimame visas STANDARD vietas zonoje A:

```sh
curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: biuru-centras-a" \
  -d '{"event_type":"ENTRY","plate":"KLB456","vehicle_type":"STANDARD","has_disability_permit":false,"preferred_zone":"A"}'

curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: biuru-centras-a" \
  -d '{"event_type":"ENTRY","plate":"MNC789","vehicle_type":"STANDARD","has_disability_permit":false,"preferred_zone":"A"}'
```

Tada dar vienas paprastas automobilis (A zonoje likusios tik EV ir DISABLED vietos):

```sh
curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: biuru-centras-a" \
  -d '{"event_type":"ENTRY","plate":"DEF001","vehicle_type":"STANDARD","has_disability_permit":false,"preferred_zone":"A"}' \
  | python3 -m json.tool
```

Tikėtinas atsakymas (`alternative_zone: true`, EV vietos A-04 ir A-05 lieka laisvos):
```json
{
    "status": "ASSIGNED",
    "zone": "B",
    "spot": "B-01",
    "spot_type": "STANDARD",
    "free_in_zone": 3,
    "alternative_zone": true,
    "error_code": null,
    "message": null
}
```

### 3. Išvažiavimas be įvažiavimo → REJECTED

```sh
curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: biuru-centras-a" \
  -d '{"event_type":"EXIT","plate":"ZZZ999","vehicle_type":"STANDARD","has_disability_permit":false,"preferred_zone":"A"}' \
  | python3 -m json.tool
```

Tikėtinas atsakymas (užimtumas nepakinta):
```json
{
    "status": "REJECTED",
    "zone": null,
    "spot": null,
    "spot_type": null,
    "free_in_zone": null,
    "alternative_zone": false,
    "error_code": "NO_ACTIVE_ENTRY",
    "message": "Automobilis ZZZ999 neturi aktyvaus įvažiavimo"
}
```

### 4. Kliento B kontekste bandoma atlaisvinti kliento A automobilį → REJECTED

```sh
curl -s -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: prekybos-centras-b" \
  -d '{"event_type":"EXIT","plate":"LTA123","vehicle_type":"STANDARD","has_disability_permit":false,"preferred_zone":"A"}' \
  | python3 -m json.tool
```

Tikėtinas atsakymas (kliento A duomenys nepakinta ir nematomi kliento B kontekste):
```json
{
    "status": "REJECTED",
    "zone": null,
    "spot": null,
    "spot_type": null,
    "free_in_zone": null,
    "alternative_zone": false,
    "error_code": "NO_ACTIVE_ENTRY",
    "message": "Automobilis LTA123 neturi aktyvaus įvažiavimo"
}
```

### 5. Nežinomas klientas → 404

```sh
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/occupancy -H "X-Tenant-ID: nera-tokio"
```

Tikėtinas atsakymas: `404`.

## API maršrutai

| Metodas | Kelias | Antraštė | Aprašas |
|---------|--------|----------|---------|
| `POST` | `/events` | `X-Tenant-ID` | Įvažiavimo arba išvažiavimo įvykis |
| `GET` | `/occupancy` | `X-Tenant-ID` | Laisvų vietų skaičius pagal zonas |
| `GET` | `/` | – | Vartų imitacijos HTML sąsaja |
| `GET` | `/docs` | – | Swagger API dokumentacija |
