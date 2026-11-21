# Thai Finance Agent

Open-source starter kit for tracking personal income, spending, investments, and Thai tax-preparation records with a local CSV dashboard.

## Quick start with Codex

1. Clone or download this repository into a private folder on your computer.
2. Copy `database.example.csv` to `database.csv` and `tax_preparation.example.csv` to `tax_preparation.csv`. Never replace existing local data files.
3. Open the folder in Codex and ask it to follow `AGENTS.md`.
4. Send a slip or statement, or say hi to get น้องเป๋าวีน's menu. The skills are in `.agents/skills/` (`income-expense`, `subscription`, `dashboard`, `pao-ween`, and the team's `finance` skill for tax screening).

The example CSV files contain headers only. The real CSV filenames, receipts, tax documents, and logs are excluded by `.gitignore`; keep those files local and inspect the staged file list before publishing changes.

## Record a transaction

Attach a receipt or type a transaction. The agent extracts the date, amount, description, and category, checks likely duplicates, and appends clear entries to the local `database.csv`. If a critical detail is uncertain, it asks before recording. Items that may matter for Thai taxes are linked to `tax_preparation.csv` and marked `needs_review` until their tax-year rules and evidence are checked.

## Thai tax guidance

See [THAI_TAX_GUIDE.md](THAI_TAX_GUIDE.md) for a practical screening guide. It distinguishes assessable income, income-related expenses, tax allowances, and tax credits; explains why ordinary personal spending is not automatically deductible; and lists evidence to check. Tax rules and temporary incentives can change each year, so the agent must verify current official Revenue Department sources before advising or calculating.

## Open the dashboard on macOS

Double-click `open-dashboard.command`. It builds `my-dashboard.html` from your local `database.csv` and opens it; no server is needed. Run it again after new entries. `my-dashboard.html` holds your data and is ignored by Git.

## Pillar 1 (income and expense) and Pillar 5 (subscription alerts)

These come from muk's [my-finance](https://github.com/mukiskaijeaw/my-finance) repo and replace the starter kit's single-skill version.

- **System-1** (`agent/`): plain Python on your machine, no network. It classifies each transaction with a confidence score: 90% and up is recorded automatically, 60 to 89% goes to Codex, below 60% asks you. It learns from earlier rows and your answers (`rules.csv`).
- **Skills** (`.agents/skills/`, mirrored for Claude Code in `.claude/skills/`): `income-expense` reads slips and statements, `subscription` finds recurring charges and warns before renewals and due dates, `dashboard` builds `my-dashboard.html` when you ask for a summary, and `pao-ween` greets you as น้องเป๋าวีน with tap-to-choose options.
- **Dashboards**: `dashboard-journal.html` (journal look) and `dashboard-folder.html` (folder tabs) read `database.csv` and `agent_state.json`; `dashboard.html` is the earlier one. `open-dashboard.command` runs `python3 agent/cli.py dashboard --open`.
- **Ledger**: `database.csv` now uses muk's 11 columns (no `model`, `token_input`, `token_output`). See `AGENTS.md`.

Try one round with synthetic data (your real data is not touched):

```sh
mkdir -p /tmp/try && cp demo/database.example.csv /tmp/try/database.csv
python3 agent/cli.py --dir /tmp/try --today 2026-11-12 ingest demo/statement-2026-11.example.csv
python3 agent/cli.py --dir /tmp/try review
python3 agent/cli.py --dir /tmp/try --today 2026-11-12 alerts --days 7
```

## Teammate agents in this repo

Two teammates' agents are included as their own folders, imported with `git subtree` so their commit history is kept:

| Folder | What it is | Source |
|---|---|---|
| `shopping-agent/` | Shopping / price-comparison agent: Codex skill in `shopping-agent/.agents/skills/shopping-agent/`, standalone demo dashboard in `shopping-agent/dashboard/`, Paoween host snapshot in `shopping-agent/integrations/paoween/` | [natanonlee/shopping-agent](https://github.com/natanonlee/shopping-agent) |
| `invest-agent/` | Proactive Wealth Coach investment agent: prompt/skill in `invest-agent/skill.md`, guide in `invest-agent/README.md`. It keeps the portfolio in a local `Port_db.csv`, which `.gitignore` keeps out of Git | [Chinnakrit-jun/AI-Agent-for-invest](https://github.com/Chinnakrit-jun/AI-Agent-for-invest) |

Each folder still follows its own README. To use one with Codex, open that folder (or point Codex at its skill file). To pull a teammate's newer changes later:

```sh
git subtree pull --prefix=shopping-agent https://github.com/natanonlee/shopping-agent.git main
git subtree pull --prefix=invest-agent https://github.com/Chinnakrit-jun/AI-Agent-for-invest.git main
```

## Privacy

This repository contains no real transaction or tax records. Local files are ignored by Git. Use synthetic data in issues and screenshots, and do not upload financial data to external services.

## License

MIT; see [LICENSE](LICENSE).
