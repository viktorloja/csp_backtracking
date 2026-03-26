from __future__ import annotations
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

Event = List[Any]  # [start:int, end:int, name:str, location:str]


def minutes_to_hhmm(m: int) -> str:
    h = m // 60
    mm = m % 60
    return f"{h:02d}:{mm:02d}"


def escape_html(s: Any) -> str:
    s = str(s)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#039;")
    )


def detect_overlaps(events: List[Event]) -> List[bool]:
    """
    Assumes events are sorted by start time.
    Returns a list of booleans: overlap[i] True if event i overlaps previous event.
    """
    overlaps = [False] * len(events)
    for i in range(1, len(events)):
        prev_end = int(events[i - 1][1])
        cur_start = int(events[i][0])
        if cur_start < prev_end:
            overlaps[i] = True
    return overlaps


def render_schedule_html_from_barrister_events(
    schedule: Dict[str, List[Event]],
    *,
    title: str = "Schedule",
    out_path: str = "schedule.html",
    show_totals: bool = True,
) -> str:
    """
    Render a standalone HTML schedule.

    Input format:
      schedule = {
        "Alice Khan": [
           [540, 600, "Block: Conference", "Court2"],
           [630, 720, "CaseA", "Court1"],
        ],
        "Ben Carter": [
           [600, 660, "CaseB", "Court2"],
        ],
      }

    Times are minutes from midnight.
    """

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize + sort events for each barrister
    normalized: Dict[str, List[Event]] = {}
    total_events = 0
    total_minutes = 0
    overlap_count = 0

    for barrister, evs in schedule.items():
        evs2 = []
        
        for e in evs:
            if len(e) != 4:
                raise ValueError(f"Event must be [start,end,name,location], got: {e}")
            start, end, name, loc = e
            start_i = int(start)
            end_i = int(end)
            if end_i < start_i:
                raise ValueError(f"Event end < start for {barrister}: {e}")
            evs2.append([start_i, end_i, str(name), str(loc)])

        evs2.sort(key=lambda x: (x[0], x[1], x[2]))
        normalized[barrister] = evs2
        total_events += len(evs2)
        total_minutes += sum((e[1] - e[0]) for e in evs2)

        ov = detect_overlaps(evs2)
        overlap_count += sum(1 for v in ov if v)

    barristers_sorted = sorted(normalized.keys(), key=lambda x: x.lower())

    # Basic KPIs
    total_hours = total_minutes / 60.0 if total_minutes else 0.0

    # ---- HTML ----
    html: List[str] = []
    html.append(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape_html(title)}</title>
<style>
  :root {{
    --bg: #0b0f14;
    --card: #121a24;
    --muted: #92a2b3;
    --text: #e7eef6;
    --border: #223041;
    --ok: #1f7a3a;
    --warn: #9b6b00;
    --bad: #a33;
  }}
  body {{
    margin: 0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
    background: var(--bg);
    color: var(--text);
  }}
  .wrap {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
  }}
  h1 {{
    margin: 0 0 6px 0;
    font-size: 22px;
  }}
  .meta {{
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 16px;
  }}
  .kpi {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 8px 0 18px 0;
  }}
  .pill {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    border: 1px solid var(--border);
    color: var(--muted);
  }}
  .pill.ok   {{ border-color: rgba(31,122,58,0.6); color: #bff3cc; }}
  .pill.warn {{ border-color: rgba(155,107,0,0.6); color: #ffe2a6; }}
  .pill.bad  {{ border-color: rgba(163,51,51,0.6); color: #ffb4b4; }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
  }}
  @media (min-width: 900px) {{
    .grid {{ grid-template-columns: 1fr 1fr; }}
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 14px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.25);
  }}
  .card h2 {{
    margin: 0 0 10px 0;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  th, td {{
    text-align: left;
    padding: 8px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }}
  th {{
    color: var(--muted);
    font-weight: 600;
    font-size: 12px;
  }}
  tr.overlap td {{
    border-bottom-color: rgba(163,51,51,0.6);
  }}
  .rowbadge {{
    display: inline-block;
    margin-left: 8px;
    padding: 1px 8px;
    border-radius: 999px;
    border: 1px solid rgba(163,51,51,0.6);
    color: #ffb4b4;
    font-size: 12px;
  }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{escape_html(title)}</h1>
  <div class="meta">Generated {escape_html(generated_at)}</div>
""")

    if show_totals:
        overlap_pill = "ok" if overlap_count == 0 else "bad"
        html.append(f"""
  <div class="kpi">
    <span class="pill ok">Barristers: {len(barristers_sorted)}</span>
    <span class="pill ok">Events: {total_events}</span>
    <span class="pill ok">Total time: {total_hours:.2f} hrs</span>
    <span class="pill {overlap_pill}">Overlaps: {overlap_count}</span>
  </div>
""")

    html.append('<div class="grid">')

    for barrister in barristers_sorted:
        evs = normalized[barrister]
        overlaps = detect_overlaps(evs)

        minutes_here = sum((e[1] - e[0]) for e in evs)
        html.append(f"""
  <div class="card">
    <h2>
      <span>{escape_html(barrister)}</span>
      <span class="pill">{len(evs)} events • {minutes_here/60.0:.2f} hrs</span>
    </h2>
""")

        if not evs:
            html.append('<div class="meta">No events.</div></div>')
            continue

        html.append("""
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Location</th>
          <th>Event</th>
          <th>Duration</th>
        </tr>
      </thead>
      <tbody>
""")

        for i, (start, end, name, loc) in enumerate(evs):
            dur = end - start
            row_class = "overlap" if overlaps[i] else ""
            badge = '<span class="rowbadge">overlap</span>' if overlaps[i] else ""
            html.append(f"""
        <tr class="{row_class}">
          <td>{minutes_to_hhmm(start)}–{minutes_to_hhmm(end)}</td>
          <td><strong>{escape_html(name)}</strong>{badge}</td>
          <td>{escape_html(loc)}</td>
          <td>{dur} min</td>
        </tr>
""")

        html.append("""
      </tbody>
    </table>
  </div>
""")

    html.append("</div></div></body></html>")

    html_str = "".join(html)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    return out_path

