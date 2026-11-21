# AgriBot

**Climate-informed crop rotation advice from NASA data, a satellite health map of each field and plant disease diagnosis from a photo, delivered by voice on WhatsApp to smallholder farmers across Côte d’Ivoire.**

[![NASA Space Apps 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-0B3D91)](https://www.spaceappschallenge.org/)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-unittest-2E7D32)](#testing-and-reproducibility)

Team **CodeX Africa** · Challenge **Field Shift: Adapting Farms with NASA Data** · Coverage **all of Côte d’Ivoire**, 33 regional and district capitals, study towns **Korhogo** (Poro) and **Bouaké** (Gbêkê)

---

## Overview

Farmers in Côte d’Ivoire decide what to sow on rain-fed land while the start of the rainy season moves by weeks from one year to the next. When a plant falls sick, there is rarely an advisor nearby to say what it is. Many of these farmers cannot read, so written or web-based advice rarely reaches them.

AgriBot closes that gap on three fronts, in all 31 regions of the country:

- **What to sow.** In the savanna of the north and centre, a transparent engine turns 25 years of NASA precipitation, temperature, humidity, wind and radiation data into a ranked comparison of crop rotations, with uncertainty ranges. In the southern forest zone, it summarises what 25 years of NASA rain measurements say about the farmer’s area.
- **Where to look.** The farmer shares the position of their field, and NASA HLS imagery returns a map of 30 m cells showing which part is weaker than usual. The satellite walks the field, so a farmer with 10 hectares only goes where the map points.
- **What is harming the plant.** The farmer sends a photo of a sick leaf. AgriBot describes the visible signs, names the most likely disease, pest or deficiency, explains what favours it and what it can do to the harvest, and gives two or three actions to take in the field that day. It never names a pesticide or any other product. In the offline app, a maize leaf model trained by the team runs on the phone itself, without network.

AgriBot delivers every answer in plain, warm French, as a WhatsApp voice note when the farmer prefers to listen, and refers the farmer to their ANADER extension advisor for serious or uncertain cases.

**Hybrid by design, with or without a network.** Connectivity in rural Côte d’Ivoire is patchy, so AgriBot works in two modes:

| Mode | When | What the farmer gets |
|---|---|---|
| **Online** | A mobile data connection is available | WhatsApp voice assistant in 33 towns: rotation advice or climate of the area, field health map, vegetation alert, photo diagnosis and free farming questions |
| **Offline** | No connection at all, after a single first visit | Installable web app in the same 33 towns: precomputed NASA-based rotation advice or climate of the area, GPS location, every message read aloud, and a maize leaf diagnosis that runs on the phone |

In offline mode the phone needs no server, no network and no language model. Voice notes for the advisor are kept on the phone and shared once the network returns.

| | |
|---|---|
| **Problem** | Shifting rains, plant diseases recognised too late, and advice that does not reach farmers who cannot read |
| **Solution** | Rotation advice and climate summaries computed from NASA data, a field health map and a vegetation alert from NASA satellite imagery, and a plant disease diagnosis from a photo, in a hybrid design: by voice on WhatsApp when online, and through an offline web app with an on-device leaf diagnosis when there is no connection at all |
| **Users** | Smallholder farmers, and the extension advisors who support them |
| **Demo deck** | [presentation/AgriBot_Presentation_EN.pdf](presentation/AgriBot_Presentation_EN.pdf), 7 slides, French version alongside |

## Features

| Feature | Description |
|---|---|
| **Nationwide coverage** | The farmer names a town or village, or shares a GPS position. A village is located with OpenStreetMap and attached to the capital of its region; a GPS position goes to the nearest of the 33 regional and district capitals, with no outside call; the bot always says which town it uses |
| **Rotation advice** | In the 12 savanna capitals of the north and centre, ranks three rotations, including the farmer’s current one, for the farmer’s town and priority: enough water, a good market or a richer soil |
| **Climate of my area** | In the 21 capitals of the southern forest zone, where the savanna rotations do not apply, summarises 25 years of NASA IMERG rain: annual rain and a dry year, the wettest months of both rainy seasons and the dip between them, and how much March to July rain varies; no rain-onset date is given there, because the onset rule is cut by its 1 March search date in the south |
| **Field health map** | The farmer sends the position of their field; AgriBot reads NASA HLS NDVI and cloud mask directly from the LP DAAC cloud for a 450 m square of 30 m cells around it, applies the vegetation-alert rule to each cell against the same dates of 2013 to last year, and sends back an image, green as usual, red weaker than usual, grey under clouds, with a short voice or text explanation, in about 30 seconds on the server, and instantly when the same field is asked again the same day. Only a position rounded to about 5 km reaches the NASA catalogue, and the exact position is never stored |
| **Vegetation alert** | Compares the latest NASA HLS images of the farmer’s area with the same dates in past years, and never guesses a cause; available at Korhogo and Bouaké, with the AppEEARS extractions for the other 31 towns submitted |
| **Photo diagnosis** | Explains what a plant photo shows, the likely problem and what to do in the field, with no product ever named, in about 3 seconds |
| **Farming conversation** | Answers free farming questions in two or three warm sentences, echoing the farmer’s words, with one concrete action and a follow-up question, and remembers the last 30 minutes of the conversation, diagnoses and advice included, so “the previous message” is understood |
| **Voice first** | Voice notes in and out. A farmer who says they cannot read or write is first reassured, “Pas de souci, ce n’est pas grave”, then hears the last message read aloud and keeps getting voice replies until they ask for text |
| **Advisor app** | Streamlit app showing every score with its source and uncertainty |
| **Offline platform** | Installable web app that works with no network after the first visit, with pictograms, voice reading and an on-device leaf diagnosis, also served by the team’s server: https://conseil-rotation-ci.netlify.app, source in [offline/](offline/) |

## NASA data

| Dataset | Access | Variables | Role |
|---|---|---|---|
| **GPM IMERG** | NASA POWER API | Daily precipitation, mean of the 9 cells around each of the 33 towns, 2001 to 2025 | Rain onset, dry spells, rain over each crop cycle, climate of the southern areas |
| **MERRA-2** | NASA POWER API | Temperature, dew point, wind speed, corrected precipitation | Crop water need; independent rain source to confirm any climate shift |
| **CERES** | NASA POWER API | Surface solar radiation | Crop water need |
| **MODIS MCD12Q1** | NASA AppEEARS | Land cover, IGBP classes | Selection of 50 vegetation points per town |
| **HLS L30 and S30** | NASA AppEEARS; NASA CMR-STAC catalogue and LP DAAC cloud storage, read directly | NDVI and Fmask quality layer, April 2013 to today | Vegetation alert; field health map, reading only the 450 m window of each image |

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
| **Field health map** | The same rule applied to each 30 m cell of a 15 by 15 window around the field, on the images of a single HLS tile; by design about one cell in ten is red in a normal year, which the message says |
| **Zones** | Savanna for the districts of Savanes, Denguélé, Woroba, Zanzan and Vallée du Bandama, forest elsewhere; a provisional rule, see the limitations |

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
- **No climate shift is announced.** IMERG finds a 22-day later onset at Korhogo in 2013-2025, while MERRA-2 finds a 22-day earlier one. Neither series is a firm arbiter here. The 2012-2013 split falls close to the change in the IMERG input constellation from the TRMM era to the GPM era, the GPM Core Observatory having launched in 2014, so the IMERG shift may partly reflect instruments rather than climate; this hypothesis is not yet tested. MERRA-2 corrected rainfall was already set aside as the main rain source because it disagrees with IMERG and the Korhogo rain gauge. We therefore read the disagreement as a data limit, not as evidence of a climate change.
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
 moteur/, climate of   moteur/alerte.py,      Groq Whisper,           Groq gpt-oss-120b,    Google Gemini
 the south             field map              local faster-whisper,   strict JSON schema,   (photos only)
 NASA POWER: IMERG,    moteur/champ.py        Aethex as fallbacks     product filter
 MERRA-2, CERES        NASA HLS, AppEEARS
                       and LP DAAC cloud
 Places: OpenStreetMap Nominatim (bot/geocodage.py), 33 capitals (moteur/lieux.py)
                                                                 │
                                                                 ▼
                                            Aethex streaming text to speech ──► OGG Opus voice note
```

**Design principle:** every recommendation, climate summary and map comes from the deterministic engine. AI models only transcribe, understand, word answers, read them aloud and look at photos.

## Offline platform

Many farms have no reliable network. The [offline/](offline/) folder holds a second, fully offline channel, built during the hackathon, served by the team’s server and published at https://conseil-rotation-ci.netlify.app. Like the bot, it covers the 33 towns: rotation advice in the 12 savanna towns, and the climate of the area, measured by NASA from 2001 to 2024, in the 21 southern towns. The farmer picks the town from their position, or by part of the country then town, four towns per screen. The field health map needs fresh NASA images and so stays online, but a map received on WhatsApp remains viewable in the conversation without network.

| Aspect | Design |
|---|---|
| **Data** | Same NASA POWER and GPM IMERG series and FAO-56 rules as the main engine; every recommendation is precomputed into `app/donnees/recommandations.json` |
| **Runtime** | Installable web app with a service worker; no server, no network and no language model once loaded |
| **Accessibility** | Pictogram on every button, every message read aloud by the phone’s built-in speech synthesis, GPS location without network, voice notes kept on the phone for the advisor |
| **Leaf diagnosis** | MobileNetV3 maize leaf model trained by the team in Google Colab on openly licensed field photos from Uganda, Tanzania and Namibia, run in the browser with ONNX Runtime Web; it answers “not sure” below its confidence threshold and refuses photos without vegetation |
| **Measured reliability** | Tested in Ghana, a country never seen in training: maize streak recognised 78 times in 100 (75 to 81), and a streak answer is right 95 times in 100; healthy leaves recognised only 26 times in 100, the model saying “not sure” 67 times in 100. These figures are shown under every answer |
| **Tests** | 22 unit tests, including FAO-56 example 18; full conversation tested in headless Chrome with the server stopped and the network cut |

Its full commit history is preserved in this repository. See [offline/README.md](offline/README.md) for details, in French.

## Use of AI

### In the product

| Model or service | Role | Constraints |
|---|---|---|
| **Groq**, `whisper-large-v3-turbo` | Transcribes farmers’ voice notes | Local `faster-whisper` (base model), then Aethex, as fallbacks |
| **Groq**, `openai/gpt-oss-120b` | Understands free answers and writes short replies to farming questions | Strict JSON schema; system prompt forbids products and speaking for ANADER; output filtered again |
| **Google Gemini**, `gemini-3.5-flash`, then `gemini-3.5-flash-lite` as fallback | First opinion on plant photos, in about 4 seconds | Called for photos only; never names a product; every answer ends with a fixed advisory notice |
| **Aethex** | **AI-generated voice** of every spoken reply | Streaming synthesis; fixed phrases cached; daily character cap |
| **MobileNetV3 leaf model**, trained by the team (offline app) | Recognises maize streak and northern leaf blight on the phone, without network | Trained in Google Colab on openly licensed datasets; answers “not sure” below threshold; reliability shown with every answer |
| **Phone speech synthesis** (offline app) | Reads messages aloud | Uses the voices already installed on the phone, through the browser’s Web Speech API |

AI never produces the rotation ranking, the scores or the vegetation alert, in either channel. Texts built from engine outputs pass a guardrail that rejects any figure, crop, disease or cause the engine did not produce.

### In development

- **AI coding assistant.** The team used Claude Code (Anthropic) throughout the hackathon to write and refactor code, tests and documentation, and to draft the presentation. The team specified each task, reviewed the changes, ran the tests and notebooks, and took every design decision, logged in [docs/decisions.md](docs/decisions.md).
- **Model training.** The offline leaf model was trained by the team in Google Colab; the notebooks are in [offline/entrainement/](offline/entrainement/).
- **Figures.** Every figure in this repository comes from code executed on NASA data or on the test images, not from a language model.
- **Images.** No AI-generated images are used. Photos come from the team and from a Canva template.
- **Prompt reuse.** The photo-diagnosis prompt was first adapted from the team’s earlier AGRI-BOT project, as declared in [docs/travail_anterieur.md](docs/travail_anterieur.md).

## Safety and privacy

| Principle | Implementation |
|---|---|
| **No product advice** | No pesticide, fertiliser, brand or dose is ever named; a filter removes any sentence that would |
| **No impersonation** | AgriBot never speaks for ANADER and refers serious or uncertain cases to the ANADER advisor |
| **Consent first** | The first message asks for consent and states that messages and photos go through AI services; “stop” erases everything |
| **Data minimisation** | Only the place name typed or said by the farmer is sent to OpenStreetMap to find a village, never the number or the rest of the message; for the field map, only a position rounded to about 5 km reaches the NASA catalogue, the exact position is kept in memory only while the map is built and for the rest of the day, and is never stored on disk; phone numbers stored only as a salted HMAC; photos and voice notes never written to disk; conversation memory kept 30 minutes in RAM only; logs record message type, age and length, never content; third-party processing under each provider’s retention policy |
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
| `EARTHDATA_TOKEN` | NASA Earthdata token to read HLS images for the field map; `~/.netrc` is used otherwise |
| `BASE_DE_DONNEES`, `URL_APPLICATION`, `PLATEFORME_URL` | Database path and links sent to farmers |

## Deployment

The [deploy/](deploy/) folder puts AgriBot on any Ubuntu 24.04 server with a single command from the developer's machine:

```bash
bash deploy/deployer.sh user@server-ip example.com   # install bot, advisor app, HTTPS and firewall
bash deploy/verifier.sh example.com                  # health, Meta webhook check, advisor app
```

| Component | Setup |
|---|---|
| **Webhook** | `https://bot.example.com/webhook`, FastAPI under systemd, restarted automatically |
| **Advisor app** | `https://app.example.com`, Streamlit under systemd |
| **Offline platform** | `https://hors-ligne.example.com`, static files of `offline/app` served by Caddy, always in sync with the repository |
| **HTTPS** | Caddy, with certificates obtained and renewed automatically |
| **Security** | Dedicated `agribot` service user, `.env` readable by that user only, firewall open on SSH, HTTP and HTTPS only, only `/webhook` and `/sante` exposed on the bot host |
| **Hardening** | Daily security updates, fail2ban, SSH key-only login once a key is installed, HTTPS security headers |
| **Operations** | Nightly backup of sessions and voice cache with 14-day retention, health check every 5 minutes with automatic restart, capped system logs |

Step-by-step guide, in French: [deploy/LISEZMOI.md](deploy/LISEZMOI.md).

**Live since 20 November 2026.** AgriBot runs around the clock on an Ubuntu 24.04 server with 4 vCPU and 8 GB of memory, deployed with these scripts. Response times read from the server log: 0.7 to 1.2 seconds for buttons and written messages. The photo diagnosis took 2.8 seconds in testing with the Flash model, down from about 80 seconds with the previous model. A field health map took 32 seconds on the server for 57 NASA images, after an immediate acknowledgement, and is instant when asked again the same day. The 12 savanna towns are prepared in 24 seconds at start-up.

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
(cd offline && ../venv/bin/python -m unittest discover -s tests -t .)   # offline platform tests
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
├── deploy/          one-command server deployment: systemd services, Caddy HTTPS, update script
└── presentation/    final deck in English and French, PDF and PowerPoint
```

## Limitations and roadmap

| Limitation | Next step |
|---|---|
| No yield or income prediction, for lack of a yield model and sourced prices | Partner with CNRA and ANADER for local yield and price data |
| Market and soil criteria rest on studies from Nigeria and Burkina Faso | Replace with studies from the Poro and Gbêkê regions |
| No agronomist has reviewed the advice yet | Review by an ANADER advisor before any field use |
| The rain onset trend at Korhogo is unresolved: the period split is close to the TRMM to GPM transition in IMERG, and MERRA-2 rainfall disagrees with local gauges | Repeat the comparison with a split after 2014, and arbitrate with Ivorian ground stations (SODEXAM) |
| Bouaké is too cloudy for the HLS vegetation alert | Add a cloud-independent source such as radar |
| The field map centres a 450 m square on the position sent, not on the true field boundary, and its 10th-percentile rule colours about one cell in ten red by design | Let the farmer trace the field boundary, and group red cells before warning |
| The vegetation alert covers only Korhogo and Bouaké; the MCD12Q1 extractions of the other 31 capitals were submitted to AppEEARS on 21 November 2026 | Submit their HLS extractions once land cover is downloaded |
| No rotation comparison yet for the southern forest zone, whose two rainy seasons and food crops need sourced rotations, which could not be read | Build southern rotations with CNRA and ANADER sources, and a second-season model |
| Savanna or forest zone is set by district, a provisional rule; the CNRA cotton-basin survey also lists localities in Marahoué and Haut-Sassandra, whose capitals are counted as forest | Refine the zone per department once a sourced map is read |
| MODIS at 500 m sees mostly savanna, so the zone alert covers the area, never a single field | The field health map now answers for a single field; extend it with the field boundary |
| The field map needs a NASA Earthdata token on the server, and such tokens expire after some weeks | Renew the token in `.env`; the bot reports the map as unavailable, never as cloudy, when no image can be read |
| The offline leaf model recognises healthy leaves only 26 times in 100 and covers maize only | Retrain on field photos from Côte d’Ivoire; add the cocoa model in preparation |
| The server address is derived from its IP through sslip.io, so it changes with the server | Move to a registered domain, so the WhatsApp webhook and the offline app address never change |

## Prior work and decisions

Work that existed before the hackathon is declared in [docs/travail_anterieur.md](docs/travail_anterieur.md). Every design decision is logged with its date and rationale in [docs/decisions.md](docs/decisions.md).

## License

No license has been chosen yet. Until one is added, all rights are reserved by team CodeX Africa.
