# Changelog

## Phase 1 — scaffolding (2026-10-03)
- Repo laid out per CLAUDE.md §3; raw uploads moved to `data/raw/` (read-only) with `MANIFEST.sha256`; manuscript to `docs/thesis/`.
- `pyproject.toml`, `config/config.yaml` (every parameter commented; unknowns are `null`), `Makefile`, `.gitignore`.
- `src/aparri/` package stubs, `io.py`, `runreport.py` (parameters, input sha256, versions, warnings).
- Smoke tests (imports, config sanity, raw-data protection, manifest integrity).
