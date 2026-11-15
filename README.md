# AgriBot, Field Shift CI

**Team CodeX Africa · NASA Space Apps Challenge 2026 · Challenge “Field Shift: Adapting Farms with NASA Data”**

AgriBot turns 25 years of NASA climate data into crop rotation advice that a farmer in northern and central Côte d’Ivoire can understand on first hearing. The farmer sends a voice note on WhatsApp, and AgriBot answers with a voice note. AgriBot also gives a cautious first opinion on a photo of a sick plant and answers general farming questions. It never recommends a pesticide or any other product, and it always refers serious cases to the farmer’s ANADER extension advisor.

The pilot covers two towns with contrasting climates, **Korhogo** in the Poro region and **Bouaké** in the Gbêkê region.

## What it does

| Feature | How it works |
|---|---|
| **Rotation advice** | Compares three rotations, including the farmer’s current one, for the farmer’s town and priority, either enough water, a good market or a richer soil |
| **Voice first** | Voice notes in and out, in simple French, for farmers who cannot read |
| **Photo diagnosis** | A short, plain explanation of what the photo shows, the likely problem, what favours it and what to do in the field, with no product named |
| **Farming conversation** | Free questions about farming, answered in two or three sentences |
| **Advisor app** | A Streamlit app that shows every score, its source and its uncertainty range |
| **Offline platform** | The same advice on a web platform for areas without a network, https://conseil-rotation-ci.netlify.app |

## NASA data

| Dataset | Access | Variables | Use |
|---|---|---|---|
| GPM IMERG | NASA POWER API | Daily precipitation, mean of the 9 cells around each town, 2001 to 2025 | Rain onset, dry spells, rain over each crop cycle |
| MERRA-2 | NASA POWER API | Temperature, dew point, wind speed, corrected precipitation | Crop water need, second rain source to confirm any change |
| CERES | NASA POWER API | Solar radiation | Crop water need |
| MODIS MCD12Q1 | NASA AppEEARS | Land cover type 1 | Choice of 50 vegetation points per town |
| HLS L30 and S30 | NASA AppEEARS | Vegetation indices and quality mask | Vegetation alert, data received, alert in progress |

NOAA GHCN-Daily rain gauges are used only as an independent check. Every source is listed in [docs/sources.md](docs/sources.md), and every downloaded series is recorded with its SHA-256 checksum.

## How the advice is computed

1. **Crop water need.** FAO-56 Penman-Monteith reference evapotranspiration from MERRA-2 and CERES, multiplied by the FAO-56 crop coefficient of each crop, day by day.
2. **Rain onset.** The first 20 mm in 3 days after 1 March, with no dry spell longer than 7 days in the following 30 days.
3. **Water criterion.** For each year from 2001 to 2025, whether IMERG rain covers the water need of each crop over its cycle, and whether a dry spell longer than 7 days hits the mid-season stage.
4. **Income and soil criteria.** Share of years in cotton, which has an organised market, and share of years with a legume. Both are hypotheses drawn from published studies, not measurements.
5. **Ranking.** The criterion chosen by the farmer weighs 0.6 and the other two 0.2 each. Every score carries a 90 % bootstrap interval, and the ranking is tested against reduced rain, a later onset, other cotton sowing dates and other cotton cycle lengths.
6. **Climate change check.** A shift between 2001-2012 and 2013-2025 is told to a farmer only if IMERG and MERRA-2 both find it, in the same direction.

## Key results

Water score from 0 to 5, higher is better, reference scenario.

| Rotation | Korhogo | Bouaké |
|---|---|---|
| Sorghum then cowpea | **4.65** | **4.35** |
| Cotton, cowpea then maize | 4.27 | 3.40 |
| Cotton then maize, current practice | 4.05 | 2.97 |

- Bouaké is more exposed to water shortage than Korhogo, with a lower water score for every rotation. Median annual rain is 1,222 mm at Korhogo, range 1,033 to 1,318 mm, and 1,120 mm at Bouaké, range 901 to 1,279 mm.
- At Bouaké, cotton then maize ranks last for water in every scenario tested. At Korhogo, the ranking changes with the cotton sowing date and cycle length, and AgriBot tells the farmer so.
- Rain onset at Korhogo ranged from 24 March in 2013 to 28 May in 2017.
- Between 2001-2012 and 2013-2025, IMERG finds a 22-day later onset at Korhogo while MERRA-2 finds a 22-day earlier one. The two NASA sources disagree, so AgriBot announces no change.

Full evaluation and limits in [docs/evaluation.md](docs/evaluation.md).

## Architecture

```
WhatsApp Cloud API
      │  signed webhook
      ▼
FastAPI server (bot/main.py)
  signature check, idempotence, salted phone hash, SQLite sessions
      │
      ▼
Dialogue state machine (bot/dialogue.py)
  ├── rotation advice ──► engine (moteur/) ──► NASA POWER, IMERG, MERRA-2, CERES
  ├── voice notes ─────► Groq Whisper, then local faster-whisper, then Aethex
  ├── conversation ────► Groq gpt-oss-120b, strict JSON, product filter
  ├── photos ──────────► Google Gemini, photos only
  └── voice replies ───► Aethex text to speech, OGG Opus
```

The advice itself always comes from the engine. The AI services only listen, speak, word answers and look at photos.

## Safety and privacy

- **No products.** No pesticide, fertiliser, brand or dose is ever named. A filter removes any sentence that would name one.
- **No impersonation.** AgriBot never speaks on behalf of ANADER and always refers serious or uncertain cases to the ANADER advisor.
- **Guardrail.** Every advice text is checked so that no figure, crop or cause appears that the engine did not produce.
- **Consent.** The first message asks for consent and says that messages and photos go through AI services. Saying “stop” erases everything.
- **Minimal storage.** Phone numbers are stored only as a salted HMAC. AgriBot never writes photos or voice notes to disk. They are sent to Groq, Google or Aethex for processing under those providers’ own retention policies.

## Repository layout

```
field-shift/
├── moteur/            NASA data, indicators, rotation engine, evaluation, AppEEARS, photo diagnosis
├── bot/               WhatsApp webhook, sessions, dialogue, WhatsApp client, terminal simulator
│   └── langage/       messages, guardrail, Groq, voice, local transcription
├── app/app.py         Streamlit app for advisors
├── notebooks/         one notebook per CRISP-DM phase, executed before each commit
├── tests/             unit tests, no network calls, recorded Meta webhooks
├── docs/              scoping, data, evaluation, sources, prior work, decision log
└── presentation/      final deck, AgriBot_Presentation_FR.pptx
```

Documentation in `docs/` is written in French.

## Getting started

Python 3.12 and `ffmpeg` are required.

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in the keys, never commit .env
mkdir -p data                 # not versioned, holds the NASA series and the bot database
venv/bin/python -m unittest discover -s tests -t .
```

### Reproduce the data and the results

```bash
venv/bin/python -m moteur.controles      # downloads missing NASA series and checks them
venv/bin/python -m moteur.indicateurs    # agroclimatic indicators for Korhogo and Bouaké
venv/bin/python -m moteur.criteres       # scores and sensitivity of the rotations
venv/bin/python -m moteur.evaluation     # evaluation of the published recommendations
venv/bin/python -m moteur.evolution      # 2001-2012 versus 2013-2025, checked with MERRA-2
venv/bin/python notebooks/executer.py    # re-runs the CRISP-DM notebooks
```

AppEEARS extractions need a NASA Earthdata account in `~/.netrc`, then `venv/bin/python -m moteur.appeears suivre`.

### Run

```bash
set -a; . ./.env; set +a
venv/bin/streamlit run app/app.py                      # advisor app, http://localhost:8501
venv/bin/python -m bot.simulateur                      # AgriBot in the terminal, no WhatsApp needed
venv/bin/uvicorn bot.main:app --host 127.0.0.1 --port 8000   # WhatsApp webhook on /webhook
```

WhatsApp requires a public HTTPS URL for the webhook, from a host or a tunnel such as ngrok. In the simulator, `/photo path.jpg`, `/position 9.45 -5.63` and `/vocal path.ogg` imitate WhatsApp messages.

### Environment variables

| Variable | Purpose |
|---|---|
| `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Cloud API |
| `SEL_NUMEROS` | Salt for hashing phone numbers |
| `GROQ_API_KEY` | Transcription, understanding and written answers |
| `GEMINI_API_KEY` or `AGENT_PLATFORM_PROJET` with `AGENT_PLATFORM_API_KEY` | Photo diagnosis, through the Gemini API or Google Cloud Agent Platform |
| `AETHEX_API_KEY`, `AETHEX_VOICE_ID`, `AETHEX_CARACTERES_PAR_JOUR` | Voice replies and daily character cap |
| `BASE_DE_DONNEES`, `URL_APPLICATION`, `PLATEFORME_URL` | Database path and links sent to the farmer |

## Limitations

- The advice predicts neither yield nor income, since no yield model or sourced crop prices are used.
- The income and soil criteria rest on studies from Nigeria and Burkina Faso, not from the Poro or Gbêkê regions.
- At Korhogo, the water ranking depends on the cotton sowing date and cycle length.
- MODIS at 500 m sees mostly savanna, so the vegetation alert follows the whole area, never a single field.
- No agronomist or ANADER advisor has reviewed the advice yet.
- The photo diagnosis is indicative only and says so in every answer.

## Prior work

Work that existed before the hackathon is declared in [docs/travail_anterieur.md](docs/travail_anterieur.md). Every design decision is logged with its date in [docs/decisions.md](docs/decisions.md).

## License

No license has been chosen yet. Until the team adds one, all rights are reserved by team CodeX Africa.
