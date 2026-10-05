# Feudsolver

A Swedish Wordfeud move finder: paste a screenshot into a local website, review the recognized board and rack, and preview the highest-scoring legal moves.

The C++ engine is a separate executable. The Python backend converts screenshots into JSON and invokes the engine with that JSON on stdin. No cloud image service or API key is needed.

## Run it

Requires Python 3.11+, CMake, and a C++17 compiler. On macOS, install Apple's command line tools if you do not already have a compiler. The optional Vision OCR fallback also uses Swift.

```sh
./scripts/setup.sh
./scripts/run.sh
```

Open **http://127.0.0.1:8000** on your Mac. Choose **Choose from Photos** or **Paste image**. On desktop, dropping an image and Cmd/Ctrl+V also work. Expand **Example position** to load the bundled board and rack without a personal screenshot.

1. Review the board and rack. Orange outlines flag uncertain board tiles. Recognition warnings also cover rack tiles.
2. Click a square to correct it; use arrow keys to navigate. Delete clears a square. Use a lowercase board letter for a zero-point blank, and `?` for a blank in your rack.
3. Click **Find best moves**. Select a result to preview its placement in green.
4. Export/import a JSON position to use the same position with the standalone engine.

`PORT=8001 ./scripts/run.sh` changes the port. The server binds to all IPv4 interfaces (`0.0.0.0`) so a phone on the same network can connect. Use `FEUD_HOST=127.0.0.1 ./scripts/run.sh` to restrict it to the Mac. This is a local-network application; authentication, production upload limits at the proxy, and public hosting are not configured.

### Use it from your phone

Keep the Mac awake, run `./scripts/run.sh`, and connect both devices to the same Wi-Fi. On the Mac, `ipconfig getifaddr en0` usually shows the Wi-Fi address (or find it in System Settings → Wi-Fi → Details → TCP/IP). On the phone, open `http://<mac-ip>:8000`; `localhost` on the phone refers to the phone itself.

**Choose from Photos** opens the system image picker so you can select a saved screenshot. The file input has no camera-capture restriction. PNG, JPEG, and WebP are supported. If the server was already running before changing its network binding, restart it. If the address still cannot be reached, check whether the macOS firewall allows incoming Python connections and whether the Wi-Fi is a guest network that isolates devices.

On phones, the bottom navigation switches between **Image**, **Board**, and **Moves**. Uploading opens the board editor automatically; solving opens the moves view. The board stays visible while you scroll through results, and Previous/Next buttons cycle placements without scrolling the page. Editing the board or rack clears outdated results. Bonus editing, import/export, and instructions are under **Board tools & help**. Recognition messages expand when tapped. Larger screens keep the side-by-side workspace.

**Paste image** reads the clipboard directly when the browser permits it. Browsers require a secure context for that API: `http://localhost` on the Mac qualifies, but `http://<mac-ip>:8000` on a phone does not. On that connection, the button reveals an editable box: touch and hold it, then choose the browser's **Paste** action. Support for exposing images through native paste varies; if no image paste is offered, use Photos. A trusted HTTPS deployment would enable the direct clipboard API on the phone (subject to its browser's paste permission). See [WebKit's clipboard documentation](https://webkit.org/blog/10855/async-clipboard-api/).

## Architecture

```text
Browser: paste / upload / edit
            │
            ▼
FastAPI: detect board → recognize tiles → JSON position
            │
            ▼ stdin
C++ executable: dictionary trie + cross-checks → ranked moves
            │ stdout JSON
            ▼
Browser: scores + placement previews
```

- `engine/main.cpp`: trie-based move generation, cross-word checks, Swedish tile values, and scoring. Searches both orientations, uses rack tiles and blanks, and checks connectivity and first-move center coverage. Premiums apply only to new tiles. Seven new tiles add 40 points. Equivalent single-tile placements are deduplicated.
- `backend/ocr.py`: detects the full-width dark-theme grid and rack, separates occupied tiles from bonus squares, and returns an editable position with confidence warnings.
- `backend/glyphs.py`: matches normalized letter shapes against the bundled Droid Sans Mono font. It retains Swedish diacritics and removes the small tile-value digits. Templates come from the typeface, not from hardcoded screenshot letters.
- `scripts/vision.swift`: optional local macOS Vision fallback for poorly matching glyphs. Linux can optionally use Tesseract with Swedish language data (`tesseract-ocr` and `tesseract-ocr-swe` on Debian/Ubuntu).
- `backend/app.py`: validates requests, runs recognition and the executable with timeouts, and serves the frontend.
- `web/`: responsive vanilla HTML/CSS/JavaScript. No Node build step. UI fonts are fetched from Google Fonts, with system-font fallbacks; screenshot data stays local.

## Standalone engine

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

build/feudsolver \
  --dictionary data/swedish.txt \
  --position examples/screenshot.json \
  --limit 20

# Or send a position on stdin:
cat examples/screenshot.json | build/feudsolver --dictionary data/swedish.txt
```

The executable returns a single JSON object on stdout. Errors are JSON on stderr with exit code 1. `--help` shows supported flags. `--limit` accepts 1–1000; the HTTP API caps returned results at 100.

Input:

```json
{
  "board": ["...............", "... 15 rows, each with exactly 15 characters ..."],
  "rack": "IVIAOHD"
}
```

The abbreviated board above illustrates the fields; use `examples/screenshot.json` for a complete, runnable position. Dots mean empty cells. Uppercase letters are ordinary tiles; lowercase letters are assigned blanks. `Å`, `Ä`, and `Ö` are UTF-8 characters, each occupying one square. The Swedish tile alphabet excludes Q and W. The rack has 1–7 letters, with `?` for a blank.

An optional `bonuses` field supplies a 15×15 array of strings: `""`, `"DL"`, `"TL"`, `"DW"`, or `"TW"`. If omitted, the standard Wordfeud layout is used. Custom/random layouts can be edited in the website's bonus mode. Existing tiles' premiums are ignored when scoring.

Output includes `moves`, `total_moves`, `dictionary_words`, and `search_ms`. Each move contains its `word`, `score`, starting `row` and `col`, `direction`, `bingo`, and newly placed `tiles` with `row`, `col`, `letter`, and `blank`. Coordinates are **zero-based**; the UI displays columns A–O and rows 1–15. `search_ms` measures move generation and ranking, excluding dictionary loading and process startup.

## Dictionary accuracy

Wordfeud states that its Swedish dictionary is based on **SAOL 15**. The official list is not bundled here. Setup downloads **Den stora svenska ordlistan (DSSO)** through `wooorm/dictionaries` and produces approximately 127,000 playable-length spelling entries. This is an approximation, **not an exact Wordfeud lexicon**. It can omit valid words and include words Wordfeud rejects. Hunspell affix rules and compound generation are not expanded. Results are exhaustive only for the supplied word list and the supplied position.

The downloader excludes names, forbidden entries, entries requiring an affix, non-tile characters, and lengths outside 2–15. It retains the unmodified dictionary, affix file, and license in the ignored `data/dictionary-source/` directory. The filtered dictionary is also ignored and can be regenerated with:

```sh
.venv/bin/python scripts/download_dictionary.py
```

To supply an appropriate word list you have permission to use, put one Swedish word per UTF-8 line into a text file:

```sh
FEUD_DICTIONARY=/absolute/path/to/words.txt ./scripts/run.sh
```

The engine also accepts `--dictionary`; no recompilation is needed. `FEUD_ENGINE` can select an alternative executable. New words formed by a move are validated; existing board words are treated as given and are not rejected for absence from the replacement dictionary.

## Scope and limitations

- This version finds the highest **immediate score**, not the strongest strategic move or a solved endgame. It does not model rack leave, unseen tiles, exchanges, opponent replies, or win probability. It suggests moves; it does not submit them to Wordfeud.
- Recognition targets full, unzoomed portrait screenshots of the classic dark board and tile font. Other themes, cropped/zoomed boards, different layouts, and low-resolution images may need manual entry. The supplied screenshot is tested at widths of 1206, 900, and 600 pixels.
- Board letters representing blanks must be checked manually and entered lowercase. An unresolved `?` on the board blocks solving. Recognition confidence is a heuristic, not a probability.
- Visible empty-square bonuses are detected by color. Premiums hidden under existing tiles use the standard layout; this does not affect scoring because existing premiums are never reused. Review empty bonuses for random boards.
- Uploads are limited to 12 MB by the application; recognition also checks image dimensions. Uploaded images are not permanently saved. The backend uses temporary tile crops that are removed after recognition.

## Validation

After setup:

```sh
.venv/bin/python -m pytest -q
```

Tests compare every generated move and its score with an independent brute-force placement/scoring implementation on small dictionaries, including rack blanks, existing blanks, cross-words, and mixed premiums. Additional cases cover Swedish characters, seven-tile bonuses, board boundaries, repeated letters, malformed inputs, API responses, and OCR against a human transcription of the example screenshot at three resolutions.

The website has also been smoke-tested in Chromium for example recognition, image paste, solving, move preview, rack edits, JSON export, and mobile layout.

## Sources and third-party assets

- Rules and scoring: <https://wordfeud.com/wfweb/help/>
- Official dictionary description: <https://wordfeud.com/dictionaries/>
- DSSO distribution (LGPL-3.0): <https://github.com/wooorm/dictionaries/tree/main/dictionaries/sv>. Source and license are saved by the downloader.
- Droid Sans Mono (Apache-2.0): <https://github.com/aosp-mirror/platform_frameworks_base/tree/master/data/fonts>. Bundled in `data/fonts/` with its license.
- nlohmann/json 3.11.3 (MIT): vendored in `engine/vendor/` with its license.

Independent project; not affiliated with Wordfeud or Svenska Akademien.
