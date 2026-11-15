# AgriBot

**Climate-informed crop rotation advice from NASA data, delivered by voice on WhatsApp to smallholder farmers in Côte d’Ivoire.**

[![NASA Space Apps 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-0B3D91)](https://www.spaceappschallenge.org/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-unittest-2E7D32)](#testing-and-reproducibility)

Team **CodeX Africa** · Challenge **Field Shift: Adapting Farms with NASA Data** · Pilot regions **Poro** (Korhogo) and **Gbêkê** (Bouaké)

---

## Overview

Farmers in northern and central Côte d’Ivoire decide what to sow on rain-fed land while the start of the rainy season moves by weeks from one year to the next. Many of them cannot read, so written or web-based advice rarely reaches them.

AgriBot closes that gap. A transparent engine turns 25 years of NASA precipitation, temperature, humidity, wind and radiation data into a ranked comparison of crop rotations, with uncertainty ranges. AgriBot then delivers the result in one or two plain French sentences, as a WhatsApp voice note, and refers the farmer to their ANADER extension advisor.

| | |
|---|---|
| **Problem** | Shifting rains, plant diseases recognised too late, and advice that does not reach farmers who cannot read |
| **Solution** | Rotation advice computed from NASA data, a vegetation alert from NASA satellite imagery, a first opinion on plant photos, all by voice on WhatsApp |
| **Users** | Smallholder farmers, and the extension advisors who support them |
| **Demo deck** | [presentation/AgriBot_Presentation_EN.pdf](presentation/AgriBot_Presentation_EN.pdf), 7 slides, French version alongside |

## Features

| Feature | Description |
|---|---|
| **Rotation advice** | Ranks three rotations, including the farmer’s current one, for the farmer’s town and priority: enough water, a good market or a richer soil |
| **Vegetation alert** | Compares the latest NASA HLS images of the farmer’s area with the same dates in past years, and never guesses a cause |
| **Photo diagnosis** | Explains what a plant photo shows, the likely problem and what to do in the field, with no product ever named |
| **Farming conversation** | Answers free farming questions in two or three sentences |
| **Voice first** | Voice notes in and out; if the farmer writes, AgriBot writes back |
| **Advisor app** | Streamlit app showing every score with its source and uncertainty |
| **Offline platform** | Installable web app that works with no network after the first visit, with pictograms, voice reading and an on-device leaf diagnosis: https://conseil-rotation-ci.netlify.app, source in [offline/](offline/) |

## NASA data

| Dataset | Access | Variables | Role |
|---|---|---|---|
| **GPM IMERG** | NASA POWER API | Daily precipitation, mean of the 9 cells around each town, 2001 to 2025 | Rain onset, dry spells, rain over each crop cycle |
| **MERRA-2** | NASA POWER API | Temperature, dew point, wind speed, corrected precipitation | Crop water need; independent rain source to confirm any climate shift |
| **CERES** | NASA POWER API | Surface solar radiation | Crop water need |
| **MODIS MCD12Q1** | NASA AppEEARS | Land cover, IGBP classes | Selection of 50 vegetation points per town |
| **HLS L30 and S30** | NASA AppEEARS | NDVI and Fmask quality layer, April 2013 to November 2026 | Vegetation alert |

NOAA GHCN-Daily rain gauges serve only as an independent check. Every source is registered in [docs/sources.md](docs/sources.md), and every downloaded series is logged with its SHA-256 checksum.

## Method

| Step | Rule |
|---|---|
| **Crop water need** | FAO-56 Penman-Monteith reference evapotranspiration from MERRA-2 and CERES, times the FAO-56 crop coefficient, day by day |
| **Rain onset** | First 20 mm in 3 days after 1 March, with no dry spell over 7 days in the next 30 days |
| **Water criterion** | Per year, whether IMERG rain covers each crop’s need over its cycle, and whether a dry spell over 7 days hits the mid-season stage |
| **Market and soil criteria** | Share of years in cotton, which has an organised market, and share of years with a legume; hypotheses from published studies |
| **Ranking** | The farmer’s priority weighs 0.6, the other criteria 0.2 each; 90 % bootstrap interval on every score |
| **Sensitivity** | Ranking re-run with 20 % less rain, a 14-day later onset, other cotton sowing dates and cycle lengths |
| **Climate shift** | A change between 2001-2012 and 2013-2025 is announced only if IMERG and MERRA-2 agree in direction and significance |
| **Vegetation alert** | Zone NDVI on each image date is the median of cloud-free HLS observations over 50 points; alert if it falls below the 10th percentile of the same calendar window in other years |

## Results

Water score from 0 to 5, higher is better, reference scenario.

| Rotation | Korhogo | Bouaké |
|---|---|---|
| Sorghum then cowpea | **4.65** | **4.35** |
| Cotton, cowpea then maize | 4.27 | 3.40 |
| Cotton then maize (current practice) | 4.05 | 2.97 |

- **Bouaké is more exposed to water shortage** for every rotation. Median annual rain: 1,222 mm at Korhogo (1,033 to 1,318), 1,120 mm at Bouaké (901 to 1,279).
- **The current practice ranks last for water in both towns.** At Bouaké it stays last in every scenario tested. At Korhogo the ranking depends on the cotton sowing date and cycle length, and AgriBot says so.
- **Rain onset at Korhogo ranged from 24 March (2013) to 28 May (2017).**
- **No climate shift is announced.** IMERG finds a 22-day later onset at Korhogo in 2013-2025, while MERRA-2 finds a 22-day earlier one.
- **Vegetation alert.** At Korhogo, vegetation on 2 November 2026 was within its usual range; over past dates the alert fires 9.5 % of the time, against 10 % by design. Bouaké is too cloudy for a reliable comparison, and AgriBot says so rather than guess.

Full evaluation and limits: [docs/evaluation.md](docs/evaluation.md).

## Architecture

```
Farmer ── WhatsApp ──► WhatsApp Cloud API ── signed webhook ──► FastAPI (bot/main.py)
                                                                 │ HMAC signature, idempotence,
                                                                 │ salted phone hash, SQLite sessions
                                                                 ▼
                                                  Dialogue state machine (bot/dialogue.py)
     ┌───────────────────────┬─────────────────────┬────────────┴──────────┬─────────────────────┐
     ▼                       ▼                     ▼                       ▼                     ▼
 Rotation engine       Vegetation alert       Speech to text          Conversation          Photo diagnosis
 moteur/               moteur/alerte.py       Groq Whisper,           Groq gpt-oss-120b,    Google Gemini
 NASA POWER: IMERG,    NASA HLS via           local faster-whisper,   strict JSON schema,   (photos only)
 MERRA-2, CERES        AppEEARS               Aethex as fallbacks     product filter
                                                                 │
                                                                 ▼
                                            Aethex streaming text to speech ──► OGG Opus voice note
```

**Design principle:** every recommendation comes from the deterministic engine. AI models only transcribe, understand, word answers, read them aloud and look at photos.

## Offline platform

Many farms have no reliable network. The [offline/](offline/) folder holds a second, fully offline channel, built during the hackathon and published at https://conseil-rotation-ci.netlify.app.

| Aspect | Design |
|---|---|
| **Data** | Same NASA POWER and GPM IMERG series and FAO-56 rules as the main engine; every recommendation is precomputed into `app/donnees/recommandations.json` |
| **Runtime** | Installable web app with a service worker; no server, no network and no language model once loaded |
| **Accessibility** | Pictogram on every button, voice reading of every message, GPS location without network, voice notes kept on the phone for the advisor |
| **Leaf diagnosis** | ONNX model run in the browser with ONNX Runtime Web; training notebooks in `offline/entrainement/` |
| **Tests** | `cd offline && python -m unittest discover -s tests -t .`, including FAO-56 example 18 |

Its full commit history is preserved in this repository. See [offline/README.md](offline/README.md) for details, in French.

## Use of AI

### In the product

| Model or service | Role | Constraints |
|---|---|---|
| **Groq**, `whisper-large-v3-turbo` | Transcribes farmers’ voice notes | Local `faster-whisper` (base model), then Aethex, as fallbacks |
| **Groq**, `openai/gpt-oss-120b` | Understands free answers and writes short replies to farming questions | Strict JSON schema; system prompt forbids products and speaking for ANADER; output filtered again |
| **Google Gemini**, `gemini-4-hydrogen` | First opinion on plant photos | Called for photos only; never names a product; every answer ends with a fixed advisory notice |
| **Aethex** | **AI-generated voice** of every spoken reply | Streaming synthesis; fixed phrases cached; daily character cap |

AI never produces the rotation ranking, the scores or the vegetation alert. Texts built from engine outputs pass a guardrail that rejects any figure, crop, disease or cause the engine did not produce.

### In development

- **AI coding assistant.** The team used Claude Code (Anthropic) throughout the hackathon to write and refactor code, tests and documentation, and to draft the presentation. The team specified each task, reviewed the changes, ran the tests and notebooks, and took every design decision, logged in [docs/decisions.md](docs/decisions.md).
- **Figures.** Every figure in this repository comes from code executed on the NASA data, not from a language model.
- **Images.** No AI-generated images are used. Photos come from the team and from a Canva template.
- **Prompt reuse.** The photo-diagnosis prompt was first adapted from the team’s earlier AGRI-BOT project, as declared in [docs/travail_anterieur.md](docs/travail_anterieur.md).

## Safety and privacy

| Principle | Implementation |
|---|---|
| **No product advice** | No pesticide, fertiliser, brand or dose is ever named; a filter removes any sentence that would |
| **No impersonation** | AgriBot never speaks for ANADER and refers serious or uncertain cases to the ANADER advisor |
| **Consent first** | The first message asks for consent and states that messages and photos go through AI services; “stop” erases everything |
| **Data minimisation** | Phone numbers stored only as a salted HMAC; photos and voice notes never written to disk; third-party processing under each provider’s retention policy |
| **Honest uncertainty** | Scores carry ranges, fragile rankings name the scenario that would change them, unavailable data is stated as such |

## Quickstart

Requirements: Python 3.12 and `ffmpeg`.

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env                 # add your keys; .env is never committed
mkdir -p data                        # NASA series and bot database, not versioned
venv/bin/python -m unittest discover -s tests -t .
```

Run:

```bash
set -a; . ./.env; set +a
venv/bin/python -m bot.simulateur                              # AgriBot in the terminal, no WhatsApp needed
venv/bin/streamlit run app/app.py                              # advisor app, http://localhost:8501
venv/bin/uvicorn bot.main:app --host 127.0.0.1 --port 8000     # WhatsApp webhook on /webhook
```

WhatsApp requires a public HTTPS URL for the webhook, from a host or a tunnel such as ngrok. In the simulator, `/photo path.jpg`, `/position 9.45 -5.63` and `/vocal path.ogg` stand in for WhatsApp messages.

### Configuration

| Variable | Purpose |
|---|---|
| `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Cloud API |
| `SEL_NUMEROS` | Salt for hashing phone numbers |
| `GROQ_API_KEY` | Transcription, understanding and written answers |
| `GEMINI_API_KEY`, or `AGENT_PLATFORM_PROJET` with `AGENT_PLATFORM_API_KEY` | Photo diagnosis through the Gemini API or Google Cloud Agent Platform |
| `AETHEX_API_KEY`, `AETHEX_VOICE_ID`, `AETHEX_CARACTERES_PAR_JOUR` | Voice synthesis and daily character cap |
| `BASE_DE_DONNEES`, `URL_APPLICATION`, `PLATEFORME_URL` | Database path and links sent to farmers |

## Testing and reproducibility

```bash
venv/bin/python -m unittest discover -s tests -t .   # unit tests, no network calls, recorded Meta webhooks
venv/bin/python -m moteur.controles                  # download missing NASA series and check them
venv/bin/python -m moteur.indicateurs                # agroclimatic indicators per town
venv/bin/python -m moteur.criteres                   # rotation scores and sensitivity
venv/bin/python -m moteur.evaluation                 # evaluation of the published recommendations
venv/bin/python -m moteur.evolution                  # 2001-2012 versus 2013-2025, checked with MERRA-2
venv/bin/python -m moteur.alerte                     # HLS vegetation alert per town
venv/bin/python notebooks/executer.py                # re-run the five CRISP-DM notebooks
```

AppEEARS extractions require a NASA Earthdata account in `~/.netrc`, then `venv/bin/python -m moteur.appeears suivre`.

## Repository layout

```
field-shift/
├── moteur/          NASA data access, indicators, rotation engine, evaluation, vegetation alert, photo diagnosis
├── bot/             WhatsApp webhook, sessions, dialogue, WhatsApp client, terminal simulator
│   └── langage/     message templates, guardrail, Groq, voice, local transcription
├── app/             Streamlit advisor app
├── notebooks/       one notebook per CRISP-DM phase
├── tests/           unit tests
├── docs/            scoping, data, evaluation, sources, prior work, decision log (in French)
├── offline/         offline web platform: precomputed advice, on-device leaf diagnosis
└── presentation/    final deck in English and French, PDF and PowerPoint
```

## Limitations and roadmap

| Limitation | Next step |
|---|---|
| No yield or income prediction, for lack of a yield model and sourced prices | Partner with CNRA and ANADER for local yield and price data |
| Market and soil criteria rest on studies from Nigeria and Burkina Faso | Replace with studies from the Poro and Gbêkê regions |
| No agronomist has reviewed the advice yet | Review by an ANADER advisor before any field use |
| IMERG and MERRA-2 disagree on the rain onset trend at Korhogo | Arbitrate with Ivorian ground stations (SODEXAM) |
| Bouaké is too cloudy for the HLS vegetation alert | Add a cloud-independent source such as radar |
| MODIS at 500 m sees mostly savanna, so the alert covers the area, never a single field | Field-level points once farmers share their location |
| The bot currently runs on a team laptop | Deploy on a cloud virtual machine with a fixed HTTPS domain |

## Prior work and decisions

Work that existed before the hackathon is declared in [docs/travail_anterieur.md](docs/travail_anterieur.md). Every design decision is logged with its date and rationale in [docs/decisions.md](docs/decisions.md).

## License

No license has been chosen yet. Until one is added, all rights are reserved by team CodeX Africa.
