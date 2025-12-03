# LinkedIn Post Insights Tool

Command-line helper that pulls CIRCPACK's LinkedIn posts, enriches them with
engagement metrics, categorizes their themes, and surfaces what the best
performing posts shared in common over the last year.

## Quick start

1. Install dependencies (Python 3.10+ recommended):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Export a valid LinkedIn Marketing API token:
   ```bash
   export LINKEDIN_ACCESS_TOKEN="YOUR_TOKEN"
   ```
3. Run the analyzer (replace the org ID with CIRCPACK's numeric identifier):
   ```bash
   python3 -m linkedin_tool.cli --organization-id 123456 --top-n 5
   ```

Use `--json` to emit structured data, `--category-config` to provide a custom
JSON mapping of categories to keywords, and `--since-days` to change the
lookback window (defaults to 365 days).
