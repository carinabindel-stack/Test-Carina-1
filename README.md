# LinkedIn Post Insights Tool

Two ways to review CIRCPACK's LinkedIn performance:

1. **Python CLI** – pulls posts via the LinkedIn REST API, hydrates engagement,
   and prints a ranked report (ideal for automation).
2. **Static Browser App** – pure HTML/CSS/JS experience that runs locally in any
   browser. Upload a JSON export (or use the sample data) to see the same
   insights without installing dependencies or exposing tokens.

---

## Option A — Python CLI (server-side analysis)

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
JSON mapping of categories to keywords, and `--since-days` to change the lookback
window (defaults to 365 days).

---

## Option B — Browser-only dashboard (HTML/CSS/JS)

1. Serve or open `web/index.html` (double-click locally or run `npx serve web`
   / `python3 -m http.server` from the repo root and visit `http://localhost:8000/web`).
2. Click **Upload LinkedIn JSON** to load a file exported from the LinkedIn API
   (any payload following the `/rest/posts` schema with engagement stats), or
   hit **Load sample data** to explore the bundled dataset.
3. Adjust the analysis settings:
   - **Top posts** – how many high performers to highlight.
   - **Lookback window** – filter posts by age.
   - **Custom categories** – optional JSON map (`{"events":["event","booth"]}`).

All computation happens in-browser: no data leaves your machine, which makes the
tool safe for sensitive engagement exports.
