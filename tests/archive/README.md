# Archived tests and test docs

The full test suite and test documentation have been archived here. Only one smoke test remains in `tests/test_startup.py` to ensure the app starts. GitHub Actions are disabled. Add testing later as needed.

- **unit/** – unit tests
- **integration/** – integration tests
- **e2e/** – end-to-end tests
- **\*.md** – test review/audit/coverage docs

To run the archived tests (e.g. locally): `PYTHONPATH=src pytest tests/archive/ -v`
