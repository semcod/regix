# Benchmark — opis działania i użycie

Framework benchmarkowy w `regix/benchmark.py` mierzy wydajność regix oraz dowolnej innej biblioteki Python. Obejmuje pięć kategorii pomiarów: czas startu, czas CLI, czas unit testów, przepustowość backendów i wydajność in-process.

---

## Szybki start

```bash
# Wszystkie zestawy
python3 -m regix.benchmark

# Tylko jeden zestaw
python3 -m regix.benchmark --suite startup
python3 -m regix.benchmark --suite cli
python3 -m regix.benchmark --suite tests
python3 -m regix.benchmark --suite backends
python3 -m regix.benchmark --suite throughput

# Wyjście JSON (do dalszej analizy)
python3 -m regix.benchmark --json

# Tekst bez kolorów (CI, logi)
python3 -m regix.benchmark --plain

# Globalny próg czasu (FAIL jeśli przekroczony)
python3 -m regix.benchmark --threshold 5.0
```

---

## Zestawy (suites)

### `startup` — czas startu i importu

Mierzy jak szybko moduły regix są dostępne po uruchomieniu procesu.

| Sonda | Co mierzy | Próg |
|---|---|---|
| `ImportProbe("regix")` | Czas `import regix` w świeżym procesie | 2.0 s |
| `ImportProbe("regix.cli")` | Czas importu CLI (typer + backends) | 3.0 s |
| `ImportProbe("regix.snapshot")` | Czas importu modułu snapshot | 2.0 s |
| `ImportProbe("regix.compare")` | Czas importu modułu compare | 2.0 s |
| `ImportProbe("regix.config")` | Czas importu konfiguracji | 1.0 s |
| `ImportProbe("regix.models")` | Czas importu modeli danych | 1.0 s |
| `ImportProbe("regix.backends")` | Czas importu backendu + rejestracji | 2.0 s |

Każda sonda uruchamia pomiar **3 razy** i bierze najlepszy wynik (best-of-3), eliminując szum systemowy.

### `cli` — czas odpowiedzi CLI

Mierzy latencję poleceń regix uruchamianych jako subprocess.

| Sonda | Co mierzy | Próg |
|---|---|---|
| `regix --help` | Czas odpowiedzi help | 3.0 s |
| `regix status` | Czas wyświetlenia statusu i backendów | 5.0 s |
| `regix snapshot HEAD` | Czas pełnego snapshot (wszystkie backendy) | 30.0 s |
| `regix compare HEAD~1 HEAD` | Czas porównania dwóch commitów | 60.0 s |
| `regix gates` | Czas sprawdzenia quality gates | 30.0 s |

### `tests` — czas unit testów

Uruchamia pytest dla całego katalogu `tests/` oraz każdego pliku testowego osobno. Pozwala wykryć który plik testowy dominuje czas całego suite'a.

```
full test suite            4.3 s   PASS
pytest test_smells.py      2.1 s   PASS   ← dominuje
pytest test_compare.py     0.9 s   PASS
pytest test_config.py      0.4 s   PASS
```

### `backends` — przepustowość backendów

Tworzy tymczasowe pliki Python z realistyczną strukturą (funkcje, klasy, docstringi) i mierzy czas `backend.collect()` na 20 plikach × 1 KB.

| Backend | Próg | Co mierzy |
|---|---|---|
| `structure` | 5.0 s | AST parsing: fan_out, call_count, symbol_count |
| `docstring` | 5.0 s | Docstring coverage na poziomie symboli |
| `architecture` | 10.0 s | Architekturalne metryki (logic_density, node_type_diversity) |
| `lizard` | 15.0 s | Cyclomatic complexity via lizard (subprocess) |
| `radon` | 15.0 s | Maintainability index via radon (subprocess) |

Raportuje: `files/sec`, `symbols found`, czas całkowity.

### `throughput` — wydajność in-process

Wywołuje kluczowe operacje regix wielokrotnie w tym samym procesie.

| Sonda | Powtórzenia | Próg | Co mierzy |
|---|---|---|---|
| `RegressionConfig.from_file()` | 100× | ≥50 ops/s | Parsowanie YAML → config |
| `snapshot.capture(HEAD)` | 3× | ≤30 s total | Pełny snapshot z backendami |
| `compare(HEAD, HEAD)` | 10× | ≥5 ops/s | Porównanie dwóch snapshotów |
| `check_gates(HEAD)` | 50× | ≥20 ops/s | Sprawdzenie quality gates |

---

## Architektura

```
regix/benchmark.py
├── BenchmarkResult        – wynik pojedynczego pomiaru (czas, status, extra)
├── BenchmarkProbe (ABC)   – abstrakcyjna sonda
│   ├── ImportProbe        – czas importu modułu (subprocess)
│   ├── CLIProbe           – czas komendy CLI (subprocess)
│   ├── UnitTestProbe      – czas pytest (subprocess)
│   ├── ThroughputProbe    – wywołania/s dowolnej funkcji (in-process)
│   └── BackendProbe       – przepustowość backend.collect() (temp files)
├── BenchmarkSuite         – kolekcja sond + runner
├── BenchmarkReporter      – wyświetlanie: rich table / plain text / JSON
├── build_regix_suite()    – domyślny zestaw sond dla regix
└── benchmark_library()    – helper do benchmarkowania dowolnej biblioteki
```

### Statusy wyników

| Status | Znaczenie |
|---|---|
| `OK` | Sonda przebiegła, brak progu |
| `PASS` | Czas ≤ próg |
| `FAIL` | Czas > próg |
| `ERROR` | Wyjątek lub brakujące narzędzie |

---

## Użycie z dowolną biblioteką

`benchmark.py` zawiera helper `benchmark_library()`, który można zaimportować do własnego skryptu:

```python
from regix.benchmark import benchmark_library, BenchmarkReporter

# Pomiar dowolnej biblioteki
suite = benchmark_library(
    module="requests",
    cli_commands=[
        ["python3", "-c", "import requests; print(requests.__version__)"],
    ],
    test_path=Path("tests/"),
    threshold_import=1.0,
    threshold_cli=2.0,
    threshold_tests=30.0,
)

results = suite.run()
BenchmarkReporter(results).print()
```

Lub własne sondy:

```python
from regix.benchmark import (
    ThroughputProbe, CLIProbe, ImportProbe, BackendProbe,
    BenchmarkSuite, BenchmarkReporter,
)

suite = BenchmarkSuite("moja-biblioteka")

# Import
suite.add(ImportProbe("django", threshold=3.0))

# CLI
suite.add(CLIProbe(["django-admin", "version"], threshold=2.0))

# Backend regix
suite.add(BackendProbe("structure", file_count=50, threshold=10.0))

# Własna funkcja
import json, pathlib
data = pathlib.Path("data.json").read_text()
suite.add(ThroughputProbe(
    label="json.loads duży plik",
    fn=lambda: json.loads(data),
    n=10_000,
    threshold_ops=5_000,  # minimum 5000 ops/s aby PASS
))

results = suite.run()
BenchmarkReporter(results).print()
```

---

## Interpretacja wyników

### Czas startu (`startup`)

```
import regix            29 ms   PASS   ← dobry wynik
import regix.cli       228 ms   PASS   ← dopuszczalny (typer + backendy)
import regix.backends  180 ms   PASS   ← rejestracja backendów
```

Duże wartości (>1 s) wskazują na zbyt wiele importów przy starcie lub powolną inicjalizację backendów.

### Czas CLI (`cli`)

```
regix --help           0.5 s   PASS
regix status           1.2 s   PASS
regix snapshot HEAD   12.3 s   PASS   ← zależy od liczby plików i backendów
regix compare         25.1 s   PASS   ← dwa snapshoty + compare
regix gates           11.8 s   PASS
```

Jeśli `regix snapshot` jest zbyt wolny, sprawdź:
- liczbę plików (exclude patterns w `regix.yaml`)
- które backendy są aktywne (`regix status`)
- czy `lizard`/`radon` używają subprocess per plik

### Czas testów (`tests`)

Jeśli jeden plik testowy zajmuje tyle co cały suite, prawdopodobnie:
- tworzy dużo plików tymczasowych
- używa powolnych fixturów (`scope="function"` zamiast `scope="session"`)
- wywołuje subprocess dla każdego testu

### Przepustowość backendów (`backends`)

| Problem | Symptom | Naprawa |
|---|---|---|
| Subprocess per plik | lizard/radon wolne | Batching (jedno wywołanie na wiele plików) |
| Brak cache AST | structure + architecture parsują oddzielnie | Współdzielony cache `ast.parse()` |
| Duże pliki | >100KB ładowane do RAM | Filtr rozmiaru w config.exclude |
| Brak backendów | `ERROR: not available` | Instalacja: `pip install lizard radon` |

### Wydajność in-process (`throughput`)

```
RegressionConfig.from_file()   2.0 s   500.0 ops/s   PASS
snapshot.capture(HEAD)        18.2 s                   PASS
compare(HEAD, HEAD)            0.3 s    33.3 ops/s    PASS
check_gates(HEAD)              0.1 s   500.0 ops/s    PASS
```

Niska wydajność `compare()` wskazuje na:
- dużą liczbę symboli w snapshocie
- kosztowne wykrywanie smelli (`detect_smells()`)
- wiele metryk do porównania per symbol

---

## Uruchamianie w CI

```yaml
# .github/workflows/benchmark.yml
- name: Performance benchmark
  run: python3 -m regix.benchmark --plain --threshold 30.0
  # Zwraca exit code 1 jeśli jakikolwiek próg przekroczony
```

```bash
# Lokalne porównanie przed/po zmianach
python3 -m regix.benchmark --json > before.json
# ... zmiany w kodzie ...
python3 -m regix.benchmark --json > after.json
```

---

## Wymagania

| Pakiet | Wymagany | Cel |
|---|---|---|
| `rich` | opcjonalny | kolorowa tabela (fallback: plain text) |
| `pytest` | opcjonalny | sonda `UnitTestProbe` |
| `lizard` | opcjonalny | sonda `BackendProbe("lizard")` |
| `radon` | opcjonalny | sonda `BackendProbe("radon")` |
| `regix` | wymagany | wszystkie sondy regix-specific |

Wszystkie sondy obsługują brakujące narzędzia — zwracają status `ERROR` zamiast rzucać wyjątek.
