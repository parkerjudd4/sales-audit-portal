# Sales Competition Audit Portal

A Streamlit-powered admin panel for flagging **out-of-market selling** and **unauthorized setter usage** in sales competitions.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch
streamlit run app.py
```

The portal opens at `http://localhost:8501`.

---

## Required Libraries

| Library | Purpose |
|---|---|
| `streamlit` | UI framework |
| `pandas` | Data manipulation |
| `openpyxl` | Excel read/write |
| `geopy` | Geocoding via Nominatim + geodesic distance |
| `rapidfuzz` | Fast fuzzy string matching |
| `plotly` | Interactive charts |
| `numpy` | Numeric utilities |

---

## Project Structure

```
audit_portal/
├── app.py                  ← Entry point
├── requirements.txt
├── geocache.json           ← Auto-created; caches geocoded coordinates
├── whitelist.csv           ← Auto-created; stores approved exceptions
├── core/
│   ├── audit.py            ← Main audit engine (Feature A + B)
│   ├── geocoder.py         ← Nominatim geocoding with disk cache
│   ├── normalizer.py       ← Address normalization + fuzzy matching
│   └── whitelist.py        ← Whitelist read/write helpers
└── ui/
    ├── styles.py           ← CSS injection
    ├── sidebar.py          ← Audit configuration sliders
    ├── upload.py           ← File upload + column mapping
    └── dashboard.py        ← Results: metrics, table, charts, whitelist
```

---

## Column Mapping

The system needs 6 fields. It auto-maps common aliases (e.g. "Rep Name" → "Sales Rep Name"). If any column can't be matched, dropdown menus appear so you can assign them manually.

| Required Field | Example Aliases Auto-Detected |
|---|---|
| Sales Rep Name | rep name, salesperson, agent name |
| Sales Rep ID | rep id, employee id, agent id |
| Customer Name | customer, client name, homeowner |
| Customer Address | address, install address, site address |
| Office City | home office, branch, market, territory |
| Round of the Competition | round, week, period |

---

## Audit Logic

### Feature A – Out-of-Market Detection
- Geocodes every customer address and office city via **Nominatim** (OpenStreetMap)
- Calculates **geodesic distance** (straight-line miles)
- Flags accounts beyond the max radius (configurable; default 75 mi)
- Medium-risk tier for distances beyond the medium threshold
- Failed geocodes → **Critical** risk flag
- Results cached in `geocache.json` — subsequent runs skip known addresses

### Feature B – Setter / Collaboration Detection
1. **Exact address duplicates** across different Rep IDs → High risk
2. **Fuzzy address matches** (configurable similarity %; default 88%) across reps → Medium risk
3. **Customer name duplicates** across reps → Medium risk
4. **Velocity spikes**: a rep's volume in a round exceeds their personal baseline × multiplier → Medium risk

---

## Persistent Files

| File | Purpose |
|---|---|
| `geocache.json` | Coordinate cache — safe to delete to force re-geocoding |
| `whitelist.csv` | Approved exceptions — whitelisted accounts are excluded from flag counts |

---

## Geocoding Notes

Nominatim (the free OpenStreetMap geocoder) requires:
- **≥1 second** between requests (enforced via the sidebar delay setting)
- A descriptive user-agent (set to `sales_audit_portal_v1`)
- No commercial/high-volume use without a self-hosted instance

For large datasets (thousands of unique addresses), consider running the portal during off-peak hours or using a paid geocoding API (e.g. Google Maps Geocoding API) by swapping out `core/geocoder.py`.
