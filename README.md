# Liftlab — AI Marketing Analyst for Retail & CPG Incrementality

> Connect a customer warehouse, get a statistically validated post-campaign incrementality report + executive narrative in minutes instead of days.

This repo is a clean-room demo built entirely on **synthetic data**. It contains no proprietary code, schemas, or data from any employer. It demonstrates the end-to-end workflow that retail/CPG CRM teams run today (and that mid-market brands can't afford to run at all).

---

## What it does

A guided 5-step pipeline:

1. **Generate population.** Synthetic household-level dataset with realistic retail attributes (division, my-needs segment, persona, facts segment, channel opt-ins, ecom indicator, rewards engagement, pre-period weekly spend).
2. **Stratified TVC split.** 90/10 (configurable) test/control split, balanced across segment + persona + channel mix + division. Falls back to random for tiny strata. Includes a post-hoc balance verification report.
3. **Multi-channel campaign simulation.** Email, push, SMS deliveries with realistic open/click/unsub rates, plus a small amount of accidental control-group contamination (real-world ops drift). A known ground-truth lift is injected on engaged test households so the analysis can recover it.
4. **Incrementality analysis.** Per-HH lift %, incremental net sales / units / visits, Welch's two-sample t-tests for significance. Segment-level breakdowns across all customer dimensions. Engagement summary and ops-efficiency check (did the test side actually get the comm? did control stay clean?).
5. **AI executive summary + Excel export.** Auto-narrated markdown summary (template-driven, with optional LLM hook) plus a multi-sheet Excel report (Executive Summary, Incrementality, Engagement, Daily Engagement, Ops Efficiency, TVC Balance, one sheet per segment dimension).

End-to-end runtime on 100K households: **~7 seconds** on a laptop.

---

## Quickstart

```powershell
# Windows PowerShell
pip install -r requirements.txt
streamlit run app.py
```

```bash
# macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501).

To run the headless smoke test (no UI):

```bash
python smoke_test.py
```

This produces `smoke_test_report.xlsx` and prints the executive summary to stdout.

### Optional: real LLM narrative

If you want the executive summary written by Claude or GPT instead of the deterministic template, set one of:

```bash
export ANTHROPIC_API_KEY=...
# or
export OPENAI_API_KEY=...
```

…then check the **"Use real LLM for narrative"** box in the sidebar. The template fallback is what makes the demo recordable offline / without API keys.

---

## Project structure

```
liftlab_demo/
├── app.py                       # Streamlit single-page UI
├── smoke_test.py                # Headless end-to-end test
├── requirements.txt
├── .streamlit/config.toml       # Dark theme
└── liftlab/
    ├── data/synthetic.py        # Synthetic population generator
    ├── splits/tvc.py            # Stratified test/control split
    ├── simulation/campaign.py   # Multi-channel send + lift simulator
    ├── analysis/
    │   ├── stats.py             # Welch's t-test, two-prop z-test
    │   ├── incrementality.py    # Lift, incrementality, p-values
    │   └── engagement.py        # Engagement summary, ops efficiency
    ├── insights/narrator.py     # Template + optional LLM narrator
    └── report/excel_writer.py   # Multi-sheet Excel deliverable
```

---

## Why this exists

A typical post-campaign incrementality analysis at a tier-1 grocer or CPG brand takes:

- **6+ analyst-hours** of SQL writing per campaign
- **A 4–6 person team** spread across data engineering, analytics, and reporting
- **2 days of turnaround** per campaign, per channel
- **Hundreds of campaigns per year** = 2,000+ analyst-days/year of pure overhead

Mid-market CPG and DTC brands skip the analysis entirely or pay an agency $50K–$200K per campaign for the same report.

Liftlab compresses this into a warehouse-native agent that runs end-to-end in minutes, with the same statistical rigor.

---

## Production roadmap

The demo runs on synthetic in-memory data. The production product will:

- Connect read-only to **BigQuery, Snowflake, Redshift, Databricks**.
- Run the SQL templates **inside the customer's warehouse** (no data movement).
- Maintain a **schema mapping layer** so each customer's column names translate to a canonical model.
- Add **pre-campaign test design** (sample-size calculator, power analysis, lookalike audience suggestions).
- Add **multi-touch attribution** for customers running concurrent campaigns.
- Add **causal diagnostics** (synthetic controls, geo-holdouts) for cases where A/B isn't possible.

---

*All numbers shown in this demo are from a synthetic data generator. No real customer information is included.*
