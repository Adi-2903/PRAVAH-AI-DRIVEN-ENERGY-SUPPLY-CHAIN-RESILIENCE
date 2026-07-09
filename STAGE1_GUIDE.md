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
└── shared/
    └── clients/
        ├── eia_client.py
        ├── gdelt_client.py
        ├── ais_client.py
        ├── ofac_client.py
        └── requirements.txt
```

---

## 🔑 Prerequisites & API Keys
Before writing code, you need to register for free developer keys for the following services:

1. **EIA API Key**: Register at https://www.eia.gov/opendata/register.php
2. **aisstream.io API Key**: Register at https://aisstream.io/

*Note: GDELT and OFAC do not require API keys, they offer open public endpoints or downloadable JSON/CSV files.*

Store your API keys locally in a `.env` file at the root of the project. **Do not commit your `.env` file to version control.**

```env
# .env
EIA_API_KEY=your_key_here
AISSTREAM_API_KEY=your_key_here
```

---

## 🛠️ Step-by-Step Tasks

### 1. EIA Client (`eia_client.py`)
- **Goal**: Fetch the latest daily Brent crude spot price.
- **Endpoint**: `https://api.eia.gov/v2/petroleum/pri/spt/data/`
- **Task**: Write a function `fetch_latest_brent_price()` that uses the `EIA_API_KEY` to grab the most recent price and date.

### 2. aisstream.io Client (`ais_client.py`)
- **Goal**: Connect to the live WebSocket feed for ship tracking.
- **Endpoint**: `wss://stream.aisstream.io/v0/stream`
- **Task**: Write a function `get_sample_ship_position()` that connects to the websocket using the `AISSTREAM_API_KEY`, listens for exactly one `PositionReport` message, prints it, and immediately closes the connection.

### 3. GDELT Client (`gdelt_client.py`)
- **Goal**: Fetch the latest 15-minute geopolitical event export.
- **Endpoint**: GDELT 2.0 Event Database (http://data.gdeltproject.org/gdeltv2/lastupdate.txt)
- **Task**: Write a function `fetch_latest_events()` that downloads the most recent zip file, extracts the CSV, parses the first row (focusing on fields like `ActionGeo_CountryCode` and `GoldsteinScale`), and returns it as a dictionary.

### 4. OFAC Client (`ofac_client.py`)
- **Goal**: Check the SDN (Specially Designated Nationals) list.
- **Endpoint**: OFAC provides a consolidated JSON/CSV list (e.g., via the US Treasury website).
- **Task**: Write a function `check_entity_sanctions(entity_name)` that downloads/parses the latest list and returns whether a sample name (e.g., a known sanctioned ship or company) is on it.

---

## ✅ Acceptance Criteria (Definition of Done)
Create a temporary script called `test_spine.py` in the `shared/clients/` folder that imports all four of your functions and runs them sequentially. 

If running `python test_spine.py` successfully prints out:
1. One crude oil price
2. One ship's latitude/longitude
3. One geopolitical event record
4. One OFAC entity check result

...then Stage 1 is complete! 🚀
