# Earnings Tracker (Google Sheets + GitHub Actions + yfinance) — Complete Setup & Operation Guide

This repository powers a **Google Sheets earnings tracker**:

- A **GitHub Actions** workflow runs daily and uses **yfinance** to fetch the **next earnings date** (and EPS estimate/actual + surprise %) for each ticker in `data/watchlist.json`, then writes and commits `data/earnings.json` to `main`.
- A **Google Apps Script** time-trigger runs daily inside your Google Sheet, pulls the latest `earnings.json` from GitHub, updates a **Master** table (`Earnings_Master`), rebuilds an **Actions** checklist (`Actions_Today`), and logs everything to `Run_Log`.

> ⚠️ Not financial advice. Earnings dates and figures can be incomplete, delayed, or wrong.

---

## 1) How it works (quick plan)

1. **GitHub**: Make sure your workflow runs and commits `data/earnings.json` daily.
2. **Google Sheets**: Create tabs + headers exactly as specified.
3. **Apps Script**: Paste the modular scripts from `apps_script/`, set `GITHUB_EARNINGS_URL`, create a daily trigger for `dailyRun`.
4. Validate:
   - `data/earnings.json` contains dates and EPS fields.
   - `Earnings_Master` updates without “rescheduling everything” when rerun.
   - `Actions_Today` shows Close/Open/Wait actions correctly.

---

## 2) High-level architecture

### 2.1 Data flow diagram

```
          +-------------------+
          | data/watchlist.json|
          +---------+---------+
                    |
                    | (GitHub Actions: daily)
                    v
          +-----------------------+
          | scripts/build_earnings|
          | _json.py (yfinance)   |
          +----------+------------+
                     |
                     | writes/commits
                     v
          +-------------------+
          | data/earnings.json|
          +---------+---------+
                    |
                    | (Apps Script: daily trigger)
                    v
        +---------------------------+
        | Google Sheet (your file)  |
        | - Watchlist               |
        | - Earnings_Master         |
        | - Actions_Today           |
        | - Run_Log                 |
        +---------------------------+
```

### 2.2 Responsibility diagram

```
GitHub (Python + Actions)                Google (Apps Script + Sheets)
------------------------                -----------------------------
Fetch earnings dates                    Reconcile into master history
Write JSON output                       Track reschedules + updates
Commit JSON to main                     Compute Close/Open actions
                                       Keep admin logging
```

---

## 3) Repository layout (what’s where)

```
.
├── .github/
│   └── workflows/
│       └── update_earnings.yml          # schedules + runs python and commits JSON
├── data/
│   ├── watchlist.json                   # input list for python job
│   └── earnings.json                    # output generated daily (committed)
├── scripts/
│   ├── __init__.py                      # required for python -m usage
│   └── build_earnings_json.py           # yfinance -> earnings.json
├── requirements.txt                     # python deps for GitHub runner
└── apps_script/
    ├── configs.gs                       # sheet names, headers, settings, github URL
    ├── utils.gs                         # date utilities + parsing helpers
    ├── sheets_io_logs.gs                # buffered logging + sheet IO helpers
    ├── github_fetch.gs                  # fetch earnings.json and normalize for pipeline
    ├── reconcile.gs                     # reschedule + upsert logic
    └── entrypoints.gs                   # dailyRun + actions rebuild
```

---

## 4) Data contracts (must match between Python and Apps Script)

### 4.1 `data/watchlist.json` (GitHub Action input)

Create/maintain:

```json
{
  "tickers": ["AAPL", "MSFT", "SAP", "BBVA.MC"]
}
```

- This list drives the GitHub Python job.
- You can keep it aligned with your Google Sheet watchlist, or treat it as the “authoritative list” and copy into the sheet.

### 4.2 `data/earnings.json` (GitHub Action output)

The JSON must contain:

- `generated_at` (string)
- `results` object mapping: `symbol -> [event]`
- Each symbol has **exactly one record** (your design)
- If yfinance has no date, record uses `date: ""` (blank)

Example:

```json
{
  "generated_at": "2026-01-19T07:00:00Z",
  "results": {
    "AAPL": [
      {
        "symbol": "AAPL",
        "date": "2026-02-01",
        "epsEstimate": 2.11,
        "epsActual": null,
        "surprisePct": null,
        "lastUpdated": "2026-01-19T07:00:00Z",
        "source": "yfinance.get_earnings_dates",
        "country": "United States",
        "note": "ok"
      }
    ],
    "SOME_TICKER": [
      {
        "symbol": "SOME_TICKER",
        "date": "",
        "epsEstimate": null,
        "epsActual": null,
        "surprisePct": null,
        "lastUpdated": "2026-01-19T07:00:00Z",
        "source": "yfinance.get_earnings_dates",
        "country": "United States",
        "note": "no earnings date"
      }
    ]
  }
}
```

Apps Script will:
- **ignore** blank dates automatically (they don’t parse),
- and will log “no upcoming earnings date” for those symbols.

---

## 5) GitHub setup (what to click, what to edit, what to replace)

### 5.1 Install Python dependencies on the runner

Ensure `requirements.txt` includes:

```
yfinance
pandas
lxml
```

`lxml` is needed because yfinance may require it for parsing in some cases.

### 5.2 Make sure workflow is recognized

Your workflow file must be at:

```
.github/workflows/update_earnings.yml
```

**If you don’t see it in the GitHub UI file tree:**
- It may be collapsed or you’re browsing a view that hides dotfolders.
- Use GitHub file search (press `t` on the repo Code page), type `update_earnings.yml`, and open it.
- Or go to the **Actions** tab — if the workflow exists, it will appear there.

### 5.3 Enable workflow write permissions (required to commit earnings.json)

Go to:

**Repo → Settings → Actions → General → Workflow permissions**

Select:
- ✅ **Read and write permissions**
- Save

This prevents the error:
`Permission denied to github-actions[bot]` / `403`.

### 5.4 Run the workflow manually to test

1. Go to **Actions**
2. Click the workflow name (e.g. “update_earnings”)
3. Click **Run workflow**
4. After it finishes:
   - check `data/earnings.json` updated in `main`

---

## 6) Google Sheets setup (tabs + headers)

### 6.1 Create these sheet tabs (exact names)

- `Watchlist`
- `Earnings_Master`
- `Actions_Today`
- `Run_Log`

### 6.2 Headers (row 1) — copy exactly

#### Watchlist (row 1)
Must include:

- `yahoo_symbols`

#### Earnings_Master (row 1)
Use exactly these headers (includes `country` and `surprise_pct`):

1. `event_id`
2. `symbol`
3. `country`
4. `earnings_date`
5. `release_time`
6. `eps_estimate`
7. `eps_actual`
8. `surprise_pct`
9. `status`
10. `replaced_by_event_id`
11. `close_date`
12. `open_date`
13. `close_done`
14. `open_done`
15. `last_updated`
16. `checked_at`
17. `source`

#### Actions_Today (row 1)
1. `event_id`
2. `symbol`
3. `country`
4. `earnings_date`
5. `required_action`
6. `action_taken`
7. `close_done`
8. `open_done`
9. `status`
10. `notes`
11. `updated_at`

#### Run_Log (row 1)
1. `timestamp`
2. `level`
3. `code`
4. `symbol_raw`
5. `symbol_yahoo`
6. `details`

---

## 7) Apps Script setup (exact steps)

### 7.1 Paste the Apps Script files

1. Open Google Sheet → **Extensions → Apps Script**
2. Create files in the Apps Script editor and paste content from repo `apps_script/`:
   - `configs.gs`
   - `utils.gs`
   - `sheets_io_logs.gs`
   - `github_fetch.gs`
   - `reconcile.gs`
   - `entrypoints.gs`
3. Save the project.

### 7.2 Set your GitHub Raw URL

In `configs.gs`, set:

```js
GITHUB_EARNINGS_URL: "https://raw.githubusercontent.com/<YOUR_USER>/<YOUR_REPO>/main/data/earnings.json",
```

Replace:
- `<YOUR_USER>` with your GitHub username
- `<YOUR_REPO>` with your repo name

Example:

```js
GITHUB_EARNINGS_URL: "https://raw.githubusercontent.com/mailliwJ/earnings-tracker/main/data/earnings.json",
```

### 7.3 Create a daily trigger for `dailyRun`

In Apps Script editor:
- Click **Triggers** (clock icon)
- **Add Trigger**
  - Choose function: `dailyRun`
  - Event source: Time-driven
  - Schedule: Daily
  - Pick a time **after** your GitHub Action runs

---

## 8) Expected behavior (correct “intended functionality”)

### 8.1 Idempotent runs (no mass reschedule on rerun)

Re-running `dailyRun()` should **not** mark events as Rescheduled unless the earnings date actually changed.

This is enforced by comparing normalized dates:
- old date from the sheet (might be a Date object) → normalized to `YYYY-MM-DD`
- new date from JSON → already `YYYY-MM-DD`

### 8.2 Past events remain in Master

Master is a historical ledger:
- past events stay
- future events update
- EPS actual and surprise update when available

### 8.3 Reschedule only on mismatch

If the upcoming earnings date changes:
- current future row becomes `Rescheduled`
- a new row is created with a new event_id
- `replaced_by_event_id` links old → new

### 8.4 EPS + Surprise updates

EPS actual and surprise can show up after the event.
Apps Script uses a small **lookback window** so that if EPS actual/surprise appears right after earnings, it can still update the correct record.

Recommended:
- `fromDate = today - 3 days`
- no effective upper bound (or very large)

### 8.5 Actions_Today rebuild

Actions_Today is rebuilt each run:
- preserves your `action_taken` and `notes` fields
- determines required action:
  - Close: between close_date and earnings_date, if close_done not true
  - Open: after open_date, if open_done not true
- optionally hides items after open_done

---

## 9) Visual completion styling (close_done AND open_done)

Recommended method: **Conditional formatting** in Google Sheets (no code required).

### 9.1 Conditional formatting formula

1. Select the whole Master data range (example: `A2:Q`)
2. Format → Conditional formatting → “Custom formula is”
3. Use the formula based on your close/open columns.

If `close_done` is column **M** and `open_done` is **N**, then:

```gs
=AND($M2=TRUE,$N2=TRUE)
```

Set style: grey fill + strikethrough.

> Adjust column letters if your sheet layout differs.

---

## 10) Troubleshooting

### 10.1 Workflow can’t commit (403)
Fix:
**Settings → Actions → General → Workflow permissions → Read and write permissions**

### 10.2 yfinance requires lxml
If logs show:
`Missing optional dependency 'lxml'`
Add `lxml` to `requirements.txt`.

### 10.3 Symbols “missing” but JSON shows a far-future date
Cause: Apps Script filtering with a lookahead window.
Fix: remove the upper bound filter (or set a huge lookahead).

### 10.4 Watchlist mismatch (sheet vs JSON)
- Apps Script uses **Google Sheet Watchlist**
- GitHub uses **data/watchlist.json**
Keep them aligned to avoid surprises.

---

## 11) What to do daily (operational routine)

- Check GitHub Actions run succeeded (optional)
- Open Google Sheet:
  - `Run_Log` shows the run completed
  - `Earnings_Master` updated
  - `Actions_Today` updated
- Use Actions_Today to record:
  - Closed / Opened / Skip

Apps Script syncs those flags back to Master on the next run.

---

## 12) Disclaimer / license

This tool is for tracking and organization only. No guarantee of correctness.  
MIT — see `LICENSE`.
