# TODO










# Analiza [README.md](cci:7://file:///home/tom/github/semcod/regix/README.md:0:0-0:0) i [SUMD.md](cci:7://file:///home/tom/github/semcod/regix/SUMD.md:0:0-0:0)

## Co już jest mocne

- **Pomiar regresji metryk** (CC, MI, coverage, length, smells) między dwoma refami — `@/home/tom/github/semcod/regix/regix/compare.py` + `@/home/tom/github/semcod/regix/regix/snapshot.py`.
- **`regix impact`** — wstępny silnik selekcji testów na bazie `git diff` + manifestów SWOP — `@/home/tom/github/semcod/regix/regix/impact.py:11-191`.
- **Architektoniczne smells** (`stub_regression`, `god_function`, `logic_drain`) wyłapują typowe patologie LLM-owe (tworzenie pustych zaślepek, przepisywanie funkcji w jedną „bóstwoklasę”).

## Główne problemy w kontekście „regresji od LLM-a”

### 1. `impact` jest sztywno powiązany z konkretnym workspace
`@/home/tom/github/semcod/regix/regix/impact.py:111-115` zawiera *hardkodowane* prefiksy:
```@/home/tom/github/semcod/regix/regix/impact.py:111-115
            allowed_prefixes = ("backend/", "frontend/", "connect-", "packages/", "services/")
            ignored_substrings = (
                "/node_modules/", "/.venv/", "/__pycache__/", "/project/", "project/",
                "/batch_", "batch_", "/reports/", "reports/", "/redeploy/", "redeploy/"
            )
```
oraz dopasowanie testów tylko jako `backend/tests/test_<stem>.py` lub `tests/test_<stem>.py`. To realnie nie zadziała poza repo, dla którego było pisane. **Brak konfiguracji** — w [regix.yaml](cci:7://file:///home/tom/github/semcod/regix/regix.yaml:0:0-0:0) nie ma żadnej sekcji `impact:`.

### 2. Brak prawdziwego grafu zależności kodu
README obiecuje „running … related dependencies of code”, ale [impact.py](cci:7://file:///home/tom/github/semcod/regix/regix/impact.py:0:0-0:0) mapuje tylko nazwę pliku → test po stem (`test_<stem>.py`). Nie ma:
- analizy `import`-ów / odwrotnego grafu zaimportowanych modułów,
- mapy „symbol zmieniony → testy, które go wołają” (call-graph / coverage map).

W repo są już `structure_backend` i `architecture_backend` z AST-em — **ten sam AST powinien zasilać impact-graph**.

### 3. `compare` patrzy na ref-y, a nie na hunki
`regix compare HEAD~1 HEAD` policzy regresje *globalnie*. Jeśli LLM zmienił 2 funkcje, raport może pokazać deltę CC w pliku z innego powodu (zmiana w innej funkcji w tym samym pliku). Brak filtra typu „pokaż regresje **tylko w symbolach pokrytych przez `git diff`**” (CLI ma `--symbol`, ale trzeba podawać ręcznie).

### 4. Brak wsparcia dla „pre-commit / pre-merge LLM gate”
Brakuje trybu „LLM produkuje patch → regix go ocenia *przed* zaaplikowaniem” — np. `regix compare HEAD --patch <file>` albo `regix review --staged`. Obecnie wymagany jest commit albo `--local` na całym working tree.

### 5. [SUMD.md](cci:7://file:///home/tom/github/semcod/regix/SUMD.md:0:0-0:0) jest zaśmiecony i nieaktualny
- `python_requires: >=3.13` w SUMD vs. `>= 3.9` w README → niespójność.
- Source map zawiera `.tox/py313/lib/python3.13/site-packages/markdown_it/...` (ponad 28 wpisów z venv). To bezużyteczne dla LLM-a używającego SUMD jako kontekstu.
- Sekcje **Dependencies** i **Intent** są w spisie treści, ale puste w pliku.
- Brakuje listy modułów [regix/](cci:9://file:///home/tom/github/semcod/regix:0:0-0:0) (są tylko testy).

### 6. Stan dokumentacyjny vs. kod
README wymienia w architekturze `regix/integrations/github.py`, ale w `@/home/tom/github/semcod/regix/regix/integrations/` są tylko 2 elementy — warto zweryfikować. Roadmap pokazuje wszystkie wersje jako `[ ]` mimo wydania `0.1.20` (badge) / `0.1.12` (SUMD) — kolejna niespójność wersji.

---

# Propozycje zmian (priorytetowo)

## P0 — zrobić `impact` użytecznym dla LLM-driven regresji

**1. Konfigurowalny impact-mapping w [regix.yaml](cci:7://file:///home/tom/github/semcod/regix/regix.yaml:0:0-0:0)**:
```yaml
impact:
  include_prefixes: ["regix/", "src/"]
  ignore_globs: ["**/.venv/**", "**/node_modules/**"]
  test_patterns:
    - "tests/test_{stem}.py"
    - "tests/**/test_{stem}.py"
    - "{dir}/tests/test_{stem}.py"
  manifests:
    swop: ".swop/manifests"
```
Zamiast hardcode'u w `@/home/tom/github/semcod/regix/regix/impact.py:111-115`.

**2. Import-graph backend** (nowy `regix/backends/import_graph.py`):
- Statyczny AST-graph `module → imported modules`.
- Odwrotny indeks: `changed_module → set(modules importujących)`.
- Rozszerzenie [analyze_impact](cci:1://file:///home/tom/github/semcod/regix/regix/impact.py:130:4-190:9) o `transitive_dependents` (BFS po grafie do zadanej głębokości).
- Test-discovery: dla każdego pliku testowego sprawdzić, jakie produkcyjne moduły importuje → mapowanie `changed_symbol → impacted_tests`.

**3. Symbol-level impact z coverage**:
- Jeśli istnieje [.coverage](cci:7://file:///home/tom/github/semcod/regix/.coverage:0:0-0:0), użyć go do mapy `test_id → set(line_ids)`.
- `regix impact --from-coverage` zwraca testy, które realnie wykonały zmienione linie hunka, nie tylko te z pasującą nazwą.

## P0 — tryb „LLM patch review”

**4. `regix review` / `regix compare --diff-only`**:
- Czyta `git diff HEAD` (lub stdin patch).
- Liczy snapshoty *tylko dla plików/symboli z patcha* (znacznie szybsze).
- Filtruje regresje: pokazuje jedynie te, których `symbol` lub `line` przecina się z hunkami patcha → eliminuje fałszywe „regresje” w sąsiednich symbolach.
- Exit code dedykowany dla CI-LLM-a (`0` = patch bezpieczny, `2` = regresja w zmienionym kodzie, `3` = regresja w zależnościach).

**5. `regix impact --run` z deltą**:
Po uruchomieniu zaznaczonych testów, wynik agregować razem z `RegressionReport`:
- `tests_failed_in_changed_scope`,
- `tests_failed_in_dependent_scope`,
- `coverage_delta_in_patch`.

## P1 — wykrywanie patologii typowych dla LLM

W `@/home/tom/github/semcod/regix/regix/smells.py` dodać heurystyki:

- **`silent_except`** — nowy `except ... : pass` / `except Exception: ...` pojawia się w patchu (wzorzec łatania testów przez LLM).
- **`assertion_loss`** — spadek liczby `assert` / `expect()` w plikach testowych między snapshotami (LLM „naprawia” test usuwając asercje).
- **`mock_inflation`** — wzrost użyć `unittest.mock` / `Mock(` w produkcyjnym kodzie.
- **`dead_branch`** — pojawienie się `if False:` / `return  # TODO` / pustych ciał funkcji niedeklarowanych jako abstract.
- **`signature_break`** — zmiana sygnatury publicznej funkcji bez aktualizacji jej wszystkich call-sites (wymaga import-graph z P0 punkt 2).

## P1 — naprawa [SUMD.md](cci:7://file:///home/tom/github/semcod/regix/SUMD.md:0:0-0:0)

**6.** Generator SUMD musi:
- ignorować [.tox/](cci:9://file:///home/tom/github/semcod/regix/.tox:0:0-0:0), [.venv/](cci:9://file:///home/tom/github/semcod/regix/.venv:0:0-0:0), `site-packages/`, [dist/](cci:9://file:///home/tom/github/semcod/regix/dist:0:0-0:0), [__pycache__/](cci:9://file:///home/tom/github/semcod/regix/regix/__pycache__:0:0-0:0) (te same `ignore_globs` co `impact`),
- wypełniać sekcje `Dependencies` (z [pyproject.toml](cci:7://file:///home/tom/github/semcod/regix/pyproject.toml:0:0-0:0)) i `Intent`,
- listować moduły [regix/](cci:9://file:///home/tom/github/semcod/regix:0:0-0:0) zamiast tylko [tests/](cci:9://file:///home/tom/github/semcod/regix/tests:0:0-0:0),
- pinować `python_requires` z [pyproject.toml](cci:7://file:///home/tom/github/semcod/regix/pyproject.toml:0:0-0:0) (źródło prawdy) zamiast statycznej wartości `>=3.13`.

## P2 — drobne porządkowe

- Synchronizacja wersji: badge `0.1.20` (README L3), SUMD `0.1.12`, [VERSION](cci:7://file:///home/tom/github/semcod/regix/VERSION:0:0-0:0) (7 B w katalogu) — ujednolicić, czytać z jednego źródła w generatorach.
- Roadmap w README — odhaczyć faktycznie wydane kamienie milowe.
- Doprecyzować w README, że `regix gates` czyta `.regix/report.{json,toon.yaml}` (obecnie nie udokumentowane).
- Uzupełnić `regix impact` w sekcji "What Regix does" / "Key features" — to teraz centralna funkcja a jest schowana tylko w CLI reference.

---

# Sugerowany minimalny pierwszy krok

Jeśli chcesz, mogę zacząć od **P0 punkt 4** (`regix review` filtrujący regresje do symboli z `git diff`) — to najmniejsza zmiana, która od razu czyni Regix użytecznym jako gate dla LLM-owych patchy, korzysta z istniejącej maszynerii [compare.py](cci:7://file:///home/tom/github/semcod/regix/regix/compare.py:0:0-0:0) i nie wymaga nowego backendu. Daj znać, czy ruszać.
**Generated by:** prefact v0.1.30
**Generated on:** 2026-04-07T20:50:02.881879
**Total issues:** 55 active, 28 completed

---

## ✅ Completed Tasks

- [x] pyproject.toml:29 - Outdated dependency: typer 0.23.1 → 0.24.1 (wheel)
- [x] pyproject.toml:30 - Outdated dependency: rich 13.7.1 → 14.3.3 (wheel)
- [x] regix/benchmark.py:21 - Unused import: 'annotations'
- [x] regix/benchmark.py:364 - Magic number: 20 - use named constant
- [x] regix/benchmark.py:710 - Magic number: 15.0 - use named constant
- [x] regix/benchmark.py:711 - Magic number: 15.0 - use named constant
- [x] regix/benchmark.py:761 - Duplicate import: 'shutil' (first at line 431)
- [x] regix/benchmark.py:779 - Duplicate import: 'RegressionConfig' (first at line 757)
- [x] regix/benchmark.py:806 - Duplicate import: 'RegressionConfig' (first at line 757)
- [x] regix/benchmark.py:935 - module execution block
- [x] regix/cli.py:3 - Unused import: 'annotations'
- [x] regix/cli.py:81 - Magic number: 20 - use named constant
- [x] regix/cli.py:116 - Duplicate import: 'capture' (first at line 49)
- [x] regix/cli.py:135 - Magic number: 50 - use named constant
- [x] regix/cli.py:141 - Function 'diff' missing return type (suggested: -> None)
- [x] regix/cli.py:150 - Duplicate import: 'do_compare' (first at line 47)
- [x] regix/cli.py:151 - Duplicate import: 'capture' (first at line 49)
- [x] regix/cli.py:191 - Function 'gates' missing return type (suggested: -> None)
- [x] regix/cli.py:235 - Function 'status' missing return type (suggested: -> None)
- [x] regix/cli.py:245 - Magic number: 40 - use named constant
- [x] regix/cli.py:333 - module execution block
- [x] regix/config.py:3 - Unused import: 'annotations'
- [x] regix/config.py:14 - Magic number: 15.0 - use named constant
- [x] regix/config.py:15 - Magic number: 20.0 - use named constant
- [x] regix/config.py:16 - Magic number: 80.0 - use named constant
- [x] regix/config.py:438 - Duplicate import: 'tomllib' (first at line 435)
- [x] regix/models.py:3 - Unused import: 'annotations'
- [x] regix/smells.py:14 - Unused import: 'annotations'

## 📋 Current Issues

- [ ] .tox/.pkg/bin/activate_this.py:42 - String concatenation can be converted to f-string
- [ ] .tox/.pkg/bin/activate_this.py:9 - Unused import: 'annotations'
- [ ] regix/__init__.py:94 - Magic number: 20 - use named constant
- [ ] .tox/py313/bin/activate_this.py:42 - String concatenation can be converted to f-string
- [ ] .tox/py313/bin/activate_this.py:9 - Unused import: 'annotations'
- [ ] regix/backends/__init__.py:3 - Unused import: 'annotations'
- [ ] regix/backends/coverage_backend.py:3 - Unused import: 'annotations'
- [ ] regix/backends/lizard_backend.py:3 - Unused import: 'annotations'
- [ ] regix/backends/lizard_backend.py:29 - Duplicate import: 'lizard' (first at line 21)
- [ ] regix/backends/lizard_backend.py:43 - Duplicate import: 'lizard' (first at line 21)
- [ ] regix/backends/architecture_backend.py:82 - String concatenation can be converted to f-string
- [ ] regix/backends/architecture_backend.py:102 - String concatenation can be converted to f-string
- [ ] regix/backends/architecture_backend.py:3 - Unused import: 'annotations'
- [ ] regix/backends/docstring_backend.py:3 - Unused import: 'annotations'
- [ ] regix/backends/radon_backend.py:3 - Unused import: 'annotations'
- [ ] regix/backends/radon_backend.py:22 - Duplicate import: 'radon' (first at line 21)
- [ ] regix/backends/radon_backend.py:30 - Duplicate import: 'radon' (first at line 21)
- [ ] regix/backends/vallm_backend.py:3 - Unused import: 'annotations'
- [ ] regix/benchmark.py:33 - Unexpected indentation
- [ ] regix/benchmark.py:35 - Expected a statement
- [ ] regix/benchmark.py:6 - module execution block
- [ ] regix/benchmark.py:525 - module execution block
- [ ] regix/backends/structure_backend.py:119 - String concatenation can be converted to f-string
- [ ] regix/backends/structure_backend.py:11 - Unused import: 'annotations'
- [ ] regix/cache.py:3 - Unused import: 'annotations'
- [ ] regix/cli.py:65 - Duplicate import: 'capture' (first at line 27)
- [ ] regix/cli.py:81 - Duplicate import: 'do_compare' (first at line 25)
- [ ] regix/cli.py:82 - Duplicate import: 'capture' (first at line 27)
- [ ] regix/cli.py:49 - Magic number: 20 - use named constant
- [ ] regix/cli.py:145 - Magic number: 40 - use named constant
- [ ] regix/cli.py:75 - Magic number: 50 - use named constant
- [ ] regix/cli.py:5 - module execution block
- [ ] regix/cli.py:175 - module execution block
- [ ] regix/compare.py:3 - Unused import: 'annotations'
- [ ] regix/config.py:345 - Duplicate import: 'tomllib' (first at line 342)
- [ ] regix/config.py:7 - Magic number: 15.0 - use named constant
- [ ] regix/config.py:8 - Magic number: 20.0 - use named constant
- [ ] regix/config.py:9 - Magic number: 30.0 - use named constant
- [ ] regix/config.py:34 - module execution block
- [ ] regix/exceptions.py:3 - Unused import: 'annotations'
- [ ] regix/gates.py:3 - Unused import: 'annotations'
- [ ] regix/git.py:31 - String concatenation can be converted to f-string
- [ ] regix/git.py:64 - String concatenation can be converted to f-string
- [ ] regix/git.py:67 - String concatenation can be converted to f-string
- [ ] regix/git.py:3 - Unused import: 'annotations'
- [ ] regix/git.py:52 - Magic number: 20 - use named constant
- [ ] regix/history.py:3 - Unused import: 'annotations'
- [ ] regix/integrations/__init__.py:3 - Unused import: 'annotations'
- [ ] regix/report.py:122 - String concatenation can be converted to f-string
- [ ] regix/report.py:3 - Unused import: 'annotations'
- [ ] regix/smells.py:52 - String concatenation can be converted to f-string
- [ ] regix/models.py:201 - String concatenation can be converted to f-string
- [ ] regix/models.py:14 - module execution block
- [ ] regix/snapshot.py:10 - Unused import: 'annotations'
- [ ] scripts/check_regression.py:95 - module execution block

---

*To execute all tasks, run: `prefact -a --execute-todos`*

## Discovered

- regix/backends/* and many modules flagged with Unused import: 'annotations' (see TODO.md Current Issues)
- .tox vendored files contain many minor lint issues (string concatenation → f-string, unused imports); consider cleaning or ignoring vendor files
