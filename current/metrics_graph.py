from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

import matplotlib.pyplot as plt


def plot_solver_barcharts_raw(
    results: Sequence[Dict[str, Any]],
    *,
    scenario_key: str = "scenario",
    solver_key: str = "solver",
    solvers: Sequence[str] = ("ortools", "backtrack"),
    metrics: Sequence[str] = ("quality", "runtime_s", "memory_mb"),
    out_dir: Optional[str] = "results/plots",
    title_prefix: str = "Solver comparison (raw)",
    log_metrics: Sequence[str] = ("runtime_s", "memory_mb"),
    dpi: int = 200,
) -> List[str]:
    """
    Plot RAW (non-normalized) grouped bar charts comparing solvers across scenarios.

    Expected `results` items look like:
      {
        "scenario": "tiny_2b_2c",
        "solver": "ortools" or "backtrack",
        "quality": 123.4,
        "runtime_s": 0.023,
        "memory_mb": 15.2,
      }

    Writes one PNG per metric and returns list of file paths.

    Notes:
      - If a value is missing for a solver/scenario/metric, it is plotted as 0.
      - For metrics listed in `log_metrics`, the y-axis uses log scale (helps readability).
    """

    scenarios = sorted({r[scenario_key] for r in results if scenario_key in r})
    solver_set = set(solvers)

    # index results by (scenario, solver)
    by_ss: Dict[tuple, Dict[str, Any]] = {}
    for r in results:
        sc = r.get(scenario_key)
        sv = r.get(solver_key)
        if sc is None or sv is None or sv not in solver_set:
            continue
        by_ss[(sc, sv)] = r

    def safe_get(sc: str, sv: str, m: str) -> float:
        r = by_ss.get((sc, sv))
        if not r:
            return 0.0
        v = r.get(m, None)
        if v is None:
            return 0.0
        try:
            return float(v)
        except Exception:
            return 0.0

    out_paths: List[str] = []
    if out_dir is not None:
        Path(out_dir).mkdir(parents=True, exist_ok=True)

    x = list(range(len(scenarios)))
    width = 0.35  # good for 2 solvers; adjust if you add more

    for metric in metrics:
        plt.figure()

        for j, sv in enumerate(solvers):
            xs = [i + (j - (len(solvers) - 1) / 2) * width for i in x]
            ys = [safe_get(sc, sv, metric) for sc in scenarios]
            plt.bar(xs, ys, width=width, label=sv)

        plt.xticks(x, scenarios, rotation=25, ha="right")
        plt.ylabel(metric)
        plt.title(f"{title_prefix} — {metric}")
        plt.legend()
        plt.tight_layout()

        if metric in set(log_metrics):
            # Avoid log(0) issues by only enabling log when all values are non-negative;
            # if zeros exist, matplotlib still works but those bars won't be visible on log scale.
            plt.yscale("log")

        if out_dir is not None:
            out_path = str(Path(out_dir) / f"{metric}_barchart_raw.png")
            plt.savefig(out_path, dpi=dpi)
            out_paths.append(out_path)

    return out_paths

results = [
    {"scenario": "tiny_2b_2c", "solver": "ortools",    "quality": 120, "runtime_s": 0.02, "memory_mb": 40},
    {"scenario": "tiny_2b_2c", "solver": "backtrack",  "quality": 118, "runtime_s": 0.15, "memory_mb": 15},
    {"scenario": "medium_10b_50c", "solver": "ortools",   "quality": 980, "runtime_s": 1.2, "memory_mb": 120},
    {"scenario": "medium_10b_50c", "solver": "backtrack", "quality": 900, "runtime_s": 25.0, "memory_mb": 60},
]

paths = plot_solver_barcharts_raw(
    results,
    metrics=("quality", "runtime_s", "memory_mb"),
    out_dir="results/plots",
    log_metrics=("runtime_s", "memory_mb")  # optional
)
print(paths)
