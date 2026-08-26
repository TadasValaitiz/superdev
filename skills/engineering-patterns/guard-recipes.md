# Guard Recipes — the teeth, copy-paste ready

Turnkey suite guards for the canon's enforcement lines. Adapt names; keep the negative
control — **a guard never observed to fail is a hope, not a guard.**

## Arrow guard (layers — canon §1)
```python
def test_kernels_import_no_io():
    for f in Path("src").rglob("*_kernel*.py"):
        src = f.read_text()
        for banned in ("import typer", "from .persistence", "import requests", "sqlite3"):
            assert banned not in src, f"{f}: kernel imports {banned}"
# negative control: a fixture kernel file containing a banned import, asserted to FAIL this check
```
(Prefer import-linter contracts where installed; this grep form needs no dependency.)

## Seam-inventory guard (types law — canon §2)
```python
def test_every_service_entrypoint_is_typed():
    import inspect
    for svc in iter_services():                       # your registry / module walk
        for name, fn in public_methods(svc):
            sig = inspect.signature(fn)
            for p in sig.parameters.values():
                assert is_frozen_model(p.annotation), f"{svc}.{name}: untyped param {p.name}"
            assert is_result_of_model(sig.return_annotation), f"{svc}.{name}: return not Result[Model]"
```

## Banned-shapes grep (canon §2)
```bash
# in a suite test via subprocess, with a negative-control fixture file:
grep -rn "dict\[str, Any\]\|\*\*kwargs" src/*/service.py src/*/domain.py && exit 1 || exit 0
```

## Lambda ban in pipelines (canon §5)
```bash
grep -rnE "(flow|compose|and_then)\(\s*lambda" src/ && exit 1 || exit 0
```

## Poisoned-input pipeline guard (canon §5)
```python
def test_pipeline_refuses_not_raises():
    for pipeline, poison in PUBLIC_PIPELINES_WITH_POISON:   # one poisoned input per family
        result = pipeline(poison)
        assert isinstance(result, Err), f"{pipeline}: raised or returned Ok on poison"
```

## Type-check-must-fail fixtures (canon §5)
Held in `tests/typecheck_fixtures/` — EXCLUDED from the main strict run; a harness test runs
the checker on each fixture and asserts nonzero exit (one deliberate stage mis-ordering per
pipeline family).

## Emitted-spellings guard (canon §6 output contract)
```python
def test_emitted_commands_exist():
    live = set(iter_registered_command_strings())
    for msg in iter_refusal_and_hint_strings():
        for cmd in extract_command_spellings(msg):
            assert cmd in live, f"refusal/hint names dead command: {cmd}"
```

## Negative-control template (wraps any guard)
```python
def test_guard_fires_on_violation(tmp_path):
    bad = tmp_path / "bad_example.py"; bad.write_text(KNOWN_VIOLATION)
    assert guard_fails_on(bad), "guard did not fire on a known violation"
```
