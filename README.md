# LinkedIn Post Insights (Static)

One-page dashboard that mirrors the earlier CLI analysis but runs entirely in your browser—no backend, no API keys, just HTML/CSS/vanilla JS.

## Try it locally

1. Clone the repo and open the folder.
2. Serve the files (pick one):
   ```bash
   # Python
   python3 -m http.server

   # or Node
   npx serve .
   ```
3. Visit `http://localhost:8000` (or whatever port your server prints) and:
   - Upload a LinkedIn JSON export (payload shaped like `/rest/posts` with engagement stats), **or**
   - Click **Load sample data** to explore the bundled dataset.
4. Adjust analysis settings:
   - **Top posts**: number of high performers to highlight.
   - **Lookback window**: days of history to include.
   - **Custom categories**: optional JSON map (e.g. `{"events":["event","booth"]}`) to override the built-in keyword themes.

All processing happens client-side, so your data never leaves the browser. Use the page as-is or host it on GitHub Pages/S3 for your team.
