# CrewAI Ngspice Book Factory

Batch pipeline that turns a JSON **chapter ledger** and Ngspice C sources into Markdown chapters using [CrewAI](https://github.com/crewAIInc/crewAI) agents (research → math draft → code draft → assemble). Runs are **resumable**: existing chapter files are skipped unless you pass `--force`.

## Layout

| Path | Role |
|------|------|
| `ngspice_book_factory.py` | CLI entry — delegates to `book_factory.cli` |
| `book_factory/` | Config merge, ledger loading, CrewAI pipeline, logging |
| `config.yaml` | Optional defaults (loaded automatically if present next to the entry script) |
| `chapter_ledger.json` | Chapter titles, output filenames, relative paths into `source_root`, prompts |
| `project_prompts_*.json` | Agent personas and task templates (Ngspice vs Kinematica variants) |
| `oracle_*.json` | Alternate ledgers for other domains (e.g. kinematica) |

## Prerequisites

- Python 3.10+ recommended (same as the rest of this repo).
- Install dependencies (minimal set used by the factory):

  ```bash
  pip install crewai PyYAML
  ```

- A **DeepSeek API** key (OpenAI-compatible client). The CLI sets `OPENAI_API_KEY` from your resolved key so CrewAI’s LLM stack can call DeepSeek.

## Configuration merge order

Later sources override earlier ones for paths and keys:

1. Code defaults (`book_factory/constants.py`, including portable `DEFAULT_SOURCE_ROOT` under `Studio-Portable-RAG/Codebase/ngspice`).
2. `crewai/config.yaml` if it exists (paths relative to the YAML file’s directory).
3. Environment variables:

   | Variable | Purpose |
   |----------|---------|
   | `NGSPICE_BOOK_SOURCE_ROOT` | Root of the C source tree referenced by the ledger |
   | `NGSPICE_BOOK_OUTPUT_DIR` | Where Markdown chapters are written |
   | `NGSPICE_BOOK_LEDGER` | Path to ledger JSON |
   | `NGSPICE_BOOK_PROJECT_PROMPTS` | Path to `project_prompts_*.json` |
   | `NGSPICE_BOOK_LOG_FILE` | Append log file (UTF-8) |
   | `NGSPICE_BOOK_LOG_LEVEL` | e.g. `INFO`, `DEBUG` |
   | `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` | API key for the LLM |

4. CLI flags (`--config`, `--source-root`, `--output-dir`, `--ledger`, `--project-prompts`, `--deepseek-api-key`, …).

**Security:** Do not commit API keys. Use `.env` (see `.env.example`), shell exports, or `--deepseek-api-key`. For machine-specific paths without editing the tracked `config.yaml`, copy it to `config.local.yaml` (ignored by git) and pass `--config config.local.yaml`, or rely on env vars.

## Running

From the **`crewai/`** directory (required so `book_factory` imports resolve):

```bash
cd crewai
export DEEPSEEK_API_KEY=…   # or copy .env.example → .env and load it
python ngspice_book_factory.py
```

Optional arguments:

- Specific chapters only: `python ngspice_book_factory.py Chapter_01.md Chapter_02.md`
- Overwrite existing outputs: `--force`
- Faster research model (uses chat instead of reasoner when supported): `CREW_FAST=1`

From the **repository root**, set `PYTHONPATH`:

```bash
export PYTHONPATH=crewai
python crewai/ngspice_book_factory.py --config crewai/config.yaml
```

Ensure `source_root` in config (or defaults) points at your Ngspice tree and that `output_dir` exists or can be created.

## Operational notes

- Long runs: `deepseek-reasoner` can pause for many minutes; the factory logs heartbeats so you can tell the process is alive.
- Edit `chapter_ledger.json` to add or reorder chapters without Python changes.
- Swap `chapter_ledger` / `project_prompts` in YAML (or use `oracle_kinematica.json` + `project_prompts_kinematica.json`) for non-Ngspice batches—adjust `source_root` and `output_dir` accordingly.
