import statistics
from typing import Sequence, Dict, List, Tuple, Optional

import matplotlib.pyplot as plt


def compute_medians_and_error_bars(
    input_sizes: Sequence[float],
    runtime_samples: Sequence[Sequence[float]],
) -> Tuple[List[float], List[float], List[float]]:
    """
    For each input size, compute:
      - median runtime
      - lower error = median - 25th percentile
      - upper error = 75th percentile - median

    runtime_samples[i] should contain repeated runtime measurements
    for input_sizes[i].
    """
    if len(input_sizes) != len(runtime_samples):
        raise ValueError("input_sizes and runtime_samples must have the same length.")

    medians: List[float] = []
    lower_errors: List[float] = []
    upper_errors: List[float] = []

    for i, samples in enumerate(runtime_samples):
        if not samples:
            raise ValueError(f"runtime_samples[{i}] is empty.")

        sorted_samples = sorted(samples)
        median = statistics.median(sorted_samples)

        if len(sorted_samples) == 1:
            q1 = median
            q3 = median
        else:
            q1, _, q3 = statistics.quantiles(sorted_samples, n=4, method="inclusive")

        medians.append(median)
        lower_errors.append(median - q1)
        upper_errors.append(q3 - median)

    return medians, lower_errors, upper_errors


def plot_multiple_runtime_medians(
    input_sizes: Sequence[float],
    algorithm_runtime_data: Dict[str, Sequence[Sequence[float]]],
    *,
    colours: Optional[Dict[str, str]] = None,
    x_label: str = "Input size",
    y_label: str = "Runtime",
    title: str = "Median Runtime vs Input Size",
    output_file: Optional[str] = None,
) -> None:
    """
    Plot multiple runtime curves with error bars.

    Parameters
    ----------
    input_sizes:
        A list like [10, 20, 30, 40]

    algorithm_runtime_data:
        Dictionary mapping algorithm name -> list of runtime sample lists.
        Example:
        {
            "Greedy": [
                [0.1, 0.11, 0.09],   # runtimes for input size 10
                [0.2, 0.21, 0.19],   # runtimes for input size 20
            ],
            "Backtracking": [
                [0.5, 0.55, 0.52],
                [1.2, 1.1, 1.3],
            ]
        }

    colours:
        Optional dictionary mapping algorithm name -> matplotlib colour string.
        Example:
        {
            "Greedy": "blue",
            "Backtracking": "red",
            "OR-Tools": "green",
        }
    """
    plt.figure(figsize=(9, 6))

    for algorithm_name, runtime_samples in algorithm_runtime_data.items():
        medians, lower_errors, upper_errors = compute_medians_and_error_bars(
            input_sizes,
            runtime_samples,
        )

        yerr = [lower_errors, upper_errors]

        colour = None
        if colours is not None and algorithm_name in colours:
            colour = colours[algorithm_name]

        plt.errorbar(
            input_sizes,
            medians,
            yerr=yerr,
            fmt="-o",
            capsize=5,
            label=algorithm_name,
            color=colour,
        )

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")

    plt.show()


if __name__ == "__main__":
    input_sizes = [10, 20, 30, 40, 50]

    algorithm_runtime_data = {
        "Greedy": [
            [0.10, 0.11, 0.09, 0.10, 0.12],
            [0.18, 0.19, 0.17, 0.20, 0.18],
            [0.28, 0.30, 0.27, 0.29, 0.31],
            [0.41, 0.43, 0.40, 0.42, 0.44],
            [0.58, 0.60, 0.57, 0.59, 0.61],
        ],
        "Local Search": [
            [0.15, 0.16, 0.14, 0.15, 0.17],
            [0.26, 0.28, 0.25, 0.27, 0.29],
            [0.40, 0.42, 0.39, 0.41, 0.43],
            [0.59, 0.61, 0.57, 0.60, 0.62],
            [0.82, 0.85, 0.80, 0.83, 0.86],
        ],
        "Backtracking": [
            [0.60, 0.62, 0.58, 0.61, 0.64],
            [1.30, 1.35, 1.25, 1.32, 1.40],
            [2.50, 2.60, 2.45, 2.55, 2.70],
            [4.80, 4.95, 4.70, 4.90, 5.10],
            [8.90, 9.10, 8.70, 9.00, 9.30],
        ],
        "OR-Tools": [
            [0.22, 0.23, 0.21, 0.22, 0.24],
            [0.35, 0.37, 0.34, 0.36, 0.38],
            [0.55, 0.57, 0.53, 0.56, 0.58],
            [0.82, 0.85, 0.80, 0.83, 0.86],
            [1.15, 1.20, 1.10, 1.17, 1.22],
        ],
    }

    colours = {
        "Greedy": "blue",
        "Local Search": "orange",
        "Backtracking": "red",
        "OR-Tools": "green",
    }

    plot_multiple_runtime_medians(
        input_sizes,
        algorithm_runtime_data,
        colours=colours,
        x_label="Number of cases",
        y_label="Runtime (seconds)",
        title="Median Runtime vs Number of Cases",
        output_file="runtime_comparison.png",
    )