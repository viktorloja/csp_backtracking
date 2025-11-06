import plotly.express as px
import pandas as pd

# Example data — your schedule output
schedule = [
    {"Case": "CaseA", "Barrister": "Barrister1", "Start": "2025-11-05", "End": "2025-11-06"},
    {"Case": "CaseB", "Barrister": "Barrister2", "Start": "2025-11-06", "End": "2025-11-08"},
    {"Case": "CaseC", "Barrister": "Barrister3", "Start": "2025-11-07", "End": "2025-11-09"},
]

df = pd.DataFrame(schedule)

# Gantt chart
fig = px.timeline(
    df,
    x_start="Start",
    x_end="End",
    y="Barrister",
    color="Case",
    title="Court Barrister Schedule"
)
fig.update_yaxes(autorange="reversed")  # Typical for Gantt charts
fig.show()