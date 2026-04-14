# 🖤 Acne Studios AI Clienteling Engine

An AI-powered marketing content pipeline that generates editorial blog posts,
personalises them into three audience segments, syncs contacts to HubSpot,
and analyses campaign performance — all from a single Streamlit interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    app.py (UI)                       │
│           Streamlit tabs: Pipeline / History / CRM   │
└────────────┬───────────────┬───────────────┬────────┘
             │               │               │
     ┌───────▼──────┐ ┌──────▼──────┐ ┌────▼──────────┐
     │  content_    │ │  crm_       │ │  analytics.py  │
     │  generator   │ │  client.py  │ │                │
     │  .py         │ │             │ │  A/B test      │
     │              │ │  HubSpot    │ │  Perf sim      │
     │  GPT-4o blog │ │  /crm/v3/   │ │  AI summary    │
     │  GPT-4o news │ │  contacts   │ │  History log   │
     │  DALL-E 3    │ │  /crm/v3/   │ │                │
     │  JSON save   │ │  notes      │ └───────┬────────┘
     └──────────────┘ └─────────────┘         │
                                               │
                               ┌───────────────▼────────┐
                               │  logs/                  │
                               │  ├─ campaign_log.json   │
                               │  └─ performance_log.json│
                               │  data/content/*.json    │
                               └─────────────────────────┘

The system follows a modular, layered architecture:
1. Presentation Layer
   - Streamlit UI (app.py)
   - User inputs, pipeline trigger, results display
2. Application Layer
   - content_generator.py (LLM + image generation)
   - analytics.py (A/B testing, performance simulation, AI insights)
3. Integration Layer
   - crm_client.py (HubSpot API integration)
4. Data Layer
   - Local JSON storage (campaign logs, performance logs, generated content)

## Pipeline Flow

1. **Input** — User provides a product/topic and credentials in the sidebar.
2. **Content Generation** — GPT-4o writes a 400-word editorial blog and three
   persona-tailored newsletters (VIP / Regular / At-Risk).
3. **Image** — DALL-E 3 generates a Halleroed-aesthetic editorial visual.
4. **Storage** — Blog + newsletters saved to `data/content/<timestamp>_<slug>.json`.
5. **CRM Sync** — Contacts upserted to HubSpot via `/crm/v3/objects/contacts/batch/upsert`.
   Each contact is tagged with their `acne_persona` property.
6. **Send** — Newsletter dispatch simulated per segment (real API hookup ready).
7. **A/B Test** — Two-proportion z-test comparing copy variants (n=1000 each).
8. **Performance** — Simulated open / CTR / unsub rates logged to `logs/performance_log.json`.
9. **AI Summary** — GPT-4o interprets results and recommends next-campaign actions.
10. **Campaign Log** — Full record (IDs, metrics, HubSpot sync status) appended locally.

## Tools & APIs

| Layer        | Tool / API                              |
|--------------|-----------------------------------------|
| LLM          | OpenAI GPT-4o                           |
| Image gen    | OpenAI DALL-E 3                         |
| CRM          | HubSpot CRM v3 REST API                 |
| A/B testing  | `statsmodels` proportions_ztest         |
| UI           | Streamlit                               |
| Storage      | Local JSON (logs/ + data/content/)      |

## Assumptions

- HubSpot token is a **Private App** token with scopes:
  `crm.objects.contacts.write`, `crm.objects.contacts.read`, `crm.objects.notes.write`.
- A custom HubSpot contact property `acne_persona` (single-line text) must exist.
  Create it at: *HubSpot → Settings → Properties → Create property*.
- Newsletter delivery is **simulated** (no transactional email provider wired up).
  The architecture supports dropping in SendGrid / HubSpot Marketing Email.
- Performance metrics are **simulated** with realistic noise around empirical
  benchmarks. In production, replace `simulate_campaign_performance()` with
  a HubSpot Reporting API or SendGrid webhook handler.

## Running Locally

```# 1. Clone / unzip the project
cd acne_clienteling

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch
streamlit run app.py
```
## Running with Pycharm

```# 1. Open the project folder in PyCharm

# 2. Open the built-in terminal

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```


Then open http://localhost:8501, enter your API keys in the sidebar, and click
**▶ Generate Full Pipeline**.

## Project Structure

```
acne_clienteling/
├── app.py                     # Streamlit UI entry point
├── requirements.txt
├── README.md
├── modules/
│   ├── content_generator.py   # GPT-4o blog, newsletters, DALL-E image, JSON save
│   ├── crm_client.py          # HubSpot contact upsert, campaign notes, local log
│   └── analytics.py           # A/B test, perf simulation, AI summary, history
├── data/
│   └── content/               # Generated content JSON files (auto-created)
└── logs/
    ├── campaign_log.json       # Campaign metadata + A/B results (auto-created)
    └── performance_log.json    # Per-campaign engagement metrics (auto-created)
```
