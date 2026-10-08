# AI naudojimas kuriant sistemą

| Etapas | Ką sugeneravai | Ką pakeičiau ir kodėl |
|--------|---------------|----------------------|
| 2 | domain modeliai (models.py, errors.py, rules.py), InMemoryRepository, ParkingAllocationService stub, 6 testai test_allocation.py | |
| 3 | ParkingAllocationService realizacija (process_event, _process_exit, _process_entry, _assign_spot, _find_best_spot), 3 papildomi testai (EV pirmenybė, EV fallback, lygus atstumas) | |
