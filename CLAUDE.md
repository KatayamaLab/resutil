# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resutil is a Python CLI tool and decorator-based library for managing scientific experiment results. Users wrap their main function with `@resutil.main()`, which automatically creates an experiment directory, captures reproducibility metadata (command, git state, dependencies), and syncs results to cloud storage.

## Build & Development

- **Package manager**: uv (with hatchling build backend)
- **Install for development**: `uv sync` (installs deps + dev deps)
- **Run tests**: `uv run pytest` or `uv run pytest tests/test_utils.py` for a single file
- **Lint**: `uv run flake8 src/`
- **Format**: `uv run black src/`
- **Type check**: `uv run mypy src/`
- **CLI entry point**: `resutil` command (defined in `pyproject.toml` as `resutil.cli:main`)
- **Publishing**: Bump version in `pyproject.toml`, merge to main, push a `v*.*.*` tag to trigger PyPI deploy

## Architecture

### Core Flow

1. `@resutil.main()` decorator (`src/resutil/main.py`) wraps user's function
2. `core.initialize()` loads config (`resutil-conf.yaml`) and creates the appropriate storage backend
3. An experiment directory is created with base26 timestamp prefix (e.g., `aapfup_20240704T191555_comment`)
4. User code runs with access to `params.ex_dir` for saving results
5. On completion, the directory is zipped and uploaded via the storage backend

### Storage Backends

All backends implement the `Storage` base class (`src/resutil/storage/storage.py`) with methods: `upload_experiment`, `download_experiment`, `get_all_experiment_names`, `get_info`.

- **GCS** (`storage/gcs/gcs.py`) - Google Cloud Storage via service account key
- **Google Drive** (`storage/gdrive/gdrive.py`) - via Google Drive API
- **Server** (`storage/server/server.py`) - Custom resutil server with JWT auth and signed URLs

### Key Modules

- `main.py` - `@resutil.main()` decorator, experiment lifecycle orchestration
- `core.py` - Upload/download logic with `ThreadPoolExecutor` for parallel transfers
- `cli/cli_main.py` - CLI subcommands (init, push, pull, add, list, rm, comment, login)
- `config_file.py` - Reads/writes `resutil-conf.yaml` project config
- `exp_file.py` - Reads/writes `resutil-exp.yaml` per-experiment metadata
- `ex_dir.py` - Experiment directory naming (base26 encoding) and management
- `git.py` - Git integration for capturing commit hash and uncommitted files
- `utils.py` - Shared helpers (user prompts, argument parsing, env var handling)

### Environment Variables

- `RESUTIL_COMMENT` - Pre-set experiment comment (skips prompt)
- `RESUTIL_NO_INTERACTIVE` - Non-interactive mode (no user prompts)
- `RESUTIIL_REMOTE` - Suppress cloud upload (note: typo is intentional, kept for backwards compat)
- `RESUTIL_DEBUG` - Use temp directory, skip upload
