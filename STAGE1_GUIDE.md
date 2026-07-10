# Pravah: Stage 1 - Live Data Spine Build Guide

Welcome to the Pravah project! Your objective for Stage 1 is to build the **Live Data Spine**. This is the foundation that all of our AI agents will rely on. We need to prove that we can successfully fetch real-world data from our primary sources before we start building complex AI logic.

## 🎯 The Objective
You need to create Python client wrappers to fetch data from four external sources:
1. **EIA (U.S. Energy Information Administration)**: For crude oil spot prices (Brent/WTI).
2. **GDELT (Global Database of Events, Language, and Tone)**: For geopolitical news and risk events.
3. **aisstream.io**: For live AIS (Automatic Identification System) ship tracking data.
4. **OFAC (Office of Foreign Assets Control)**: For sanctions lists and entity screening.

Your goal is to write a script for each source that successfully authenticates (if required), hits the API, pulls **one real record**, and prints it to the console.

---

## 📂 Where to Work
All of your code for this stage should go into the `shared/clients/` directory.

```text
pravah/
├── .env                                (never committed — see .gitignore below)
├── .env.example                        (committed — blank template for teammates)
├── .gitignore
└── shared/
    └── clients/
        ├── eia_client.py
        ├── gdelt_client.py
        ├── ais_client.py
        ├── ofac_client.py
        ├── test_spine.py
        └── requirements.txt
```

---

## 🔑 Prerequisites & API Keys

### 1. Register for keys
1. **EIA API Key**: Register at https://www.eia.gov/opendata/register.php
2. **aisstream.io API Key**: Register at https://aisstream.io/ (sign in via GitHub, then generate a key on the API Keys page)

*Note: GDELT and OFAC do not require API keys — they offer open public endpoints or downloadable JSON/CSV files.*

### 2. `.env` — never committed
```env
# .env
EIA_API_KEY=your_key_here
AISSTREAM_API_KEY=your_key_here
```

### 3. `.env.example` — commit this one
So every teammate knows exactly what to fill in without guessing variable names:
```env
# .env.example
EIA_API_KEY=
AISSTREAM_API_KEY=
```

### 4. `.gitignore`
Add this at the repo root **before anyone commits anything** — someone will leak a key otherwise:
```gitignore
.env
__pycache__/
*.pyc
.venv/
*.zip
*.csv
```
(The `*.zip`/`*.csv` lines matter because both the GDELT and OFAC clients will download large files locally — you don't want those in git history.)

### 5. `requirements.txt`
Pin this now so nobody wastes time on import errors:
```text
requests
websockets
python-dotenv
pandas
```
Note: `websockets` (async), not `websocket-client` — aisstream's own examples are async, and pairing with `asyncio` makes the timeout handling in Step 2 much cleaner.

---

## 🛠️ Step-by-Step Tasks

### 1. EIA Client (`eia_client.py`)
- **Goal**: Fetch the latest daily Brent crude spot price.
- **Endpoint**: `https://api.eia.gov/v2/petroleum/pri/spt/data/`
- **Task**: Write a function `fetch_latest_brent_price()` that uses the `EIA_API_KEY` to grab the most recent price and date.
- **Watch out**: EIA v2 requires specific query params, not just a bare `GET`. You need:
  - `frequency=daily`
  - `data[0]=value`
  - `facets[product][]=EPCBRENT` (Brent) — check the EIA docs for the exact product code if this changes
  - `sort[0][column]=period&sort[0][direction]=desc`
  - `offset=0&length=1`
  - `api_key={EIA_API_KEY}`
  This combination is the most common stumbling block with this API — a bare request to the endpoint with no params will return a schema description, not data.

### 2. aisstream.io Client (`ais_client.py`)
- **Goal**: Connect to the live WebSocket feed for ship tracking.
- **Endpoint**: `wss://stream.aisstream.io/v0/stream`
- **Task**: Write an async function `get_sample_ship_position()` that connects to the websocket using the `AISSTREAM_API_KEY`, listens for exactly one `PositionReport` message, prints it, and immediately closes the connection.
- **Watch out — three things that will cost you time if missed**:
  1. **Set a bounding box.** Don't subscribe to the whole world (up to ~300 msgs/sec). Default to a bounding box around a chokepoint you actually care about, e.g. the Strait of Hormuz:
     ```python
     BoundingBoxes: [[[24.0, 55.5], [27.5, 57.5]]]
     ```
     This also means your Stage 1 "one record" output is already the geography your risk-agent will use later, not a random ship anywhere on Earth.
  2. **Send your subscription within 3 seconds of opening the socket**, or aisstream closes the connection. Structure the code so the subscribe message goes out immediately in the `on_open`/connect step, not after any other setup.
  3. **Add a timeout.** If the bounding box is quiet, "listen for exactly one message" will hang forever. Wrap the receive loop in `asyncio.wait_for(..., timeout=15)` and print a clear "no ship seen in this window — try a busier bounding box or wait" message instead of a frozen terminal.

### 3. GDELT Client (`gdelt_client.py`)
- **Goal**: Fetch the latest 15-minute geopolitical event export.
- **Endpoint**: GDELT 2.0 Event Database (http://data.gdeltproject.org/gdeltv2/lastupdate.txt)
- **Task**: Write a function `fetch_latest_events()` that downloads the most recent zip file, extracts the CSV, parses the first row (focusing on fields like `ActionGeo_CountryCode` and `GoldsteinScale`), and returns it as a dictionary.
- **Watch out**: `lastupdate.txt` returns **three lines**, not one — the events export, the mentions export, and the GKG export, in that order. You want the **events** export, so take the **first line**. Grabbing the wrong line is an easy silent mistake since all three are valid zip URLs.

### 4. OFAC Client (`ofac_client.py`)
- **Goal**: Check the SDN (Specially Designated Nationals) list.
- **Endpoint**: OFAC provides a consolidated JSON/CSV list (e.g., via the US Treasury website).
- **Task**: Write a function `check_entity_sanctions(entity_name)` that downloads/parses the latest list and returns whether a sample name (e.g., a known sanctioned ship or company) is on it.
- **Watch out**:
  - The SDN file is large — cache it locally after the first download (respecting `.gitignore` above) so you're not re-downloading it on every test run during dev.
  - Hardcode one **known-sanctioned name** as a fixed test case, independent of your matching logic. This way, if your string-matching logic has a bug, your test doesn't silently return `False` and pass anyway.

---

## ✅ Acceptance Criteria (Definition of Done)
Create `test_spine.py` in the `shared/clients/` folder that imports all four functions and runs them sequentially.

**Wrap each call individually** — don't let one flaky source (aisstream in particular is still in beta with no uptime SLA) crash the whole script and hide the other three results:

```python
sources = {
    "EIA (crude price)": fetch_latest_brent_price,
    "GDELT (event record)": fetch_latest_events,
    "aisstream (ship position)": get_sample_ship_position,  # async — call via asyncio.run()
    "OFAC (sanctions check)": lambda: check_entity_sanctions("SOME_KNOWN_SANCTIONED_NAME"),
}

for label, fn in sources.items():
    try:
        result = fn()
        print(f"✅ {label}: {result}")
    except Exception as e:
        print(f"❌ {label}: {e}")
```

If running `python test_spine.py` successfully prints out:
1. One crude oil price
2. One ship's latitude/longitude (from your chosen bounding box)
3. One geopolitical event record
4. One OFAC entity check result (including your hardcoded known-sanctioned test case)

...with clear ✅/❌ per source — then Stage 1 is complete! 🚀

A partial pass (3 of 4 ✅) still means real progress is visible under time pressure — fix the ❌ next rather than treating the whole script as blocked.