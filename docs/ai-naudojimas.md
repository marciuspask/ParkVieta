# AI naudojimas kuriant sistemą

| Etapas | Ką sugeneravai | Ką pakeičiau ir kodėl |
|--------|---------------|----------------------|
| 2 | domain modeliai (models.py, errors.py, rules.py), InMemoryRepository, ParkingAllocationService stub, 6 testai test_allocation.py | |
| 3 | ParkingAllocationService realizacija (process_event, _process_exit, _process_entry, _assign_spot, _find_best_spot), 3 papildomi testai (EV pirmenybė, EV fallback, lygus atstumas) | |
| 4 | PostgreSQLRepository, ORM modeliai (orm_models.py), db/database.py, seed.py dviem klientams, test_tenant_isolation.py (2 testai su skipif), .gitignore, AllocationStatus.RELEASED, _nearest pagalbinis metodas | |
| 4b | claim_spot(FOR UPDATE + patikrinimas), lygiagretumo testas su threading.Barrier, UniqueConstraint(tenant_id,spot_id) active_parkings, docker-compose.yml, db/init.sql, TEST_DATABASE_URL atskyrimas | |
| 4c | conftest.py su dotenv, pytest.fail() vietoj skipif, .env su TEST_DATABASE_URL | |
