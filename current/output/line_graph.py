import statistics
from typing import Sequence, List, Tuple, Optional

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

    Returns:
        medians, lower_errors, upper_errors
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

        # statistics.quantiles returns quartile cut points
        # method='inclusive' is usually nicer for small experimental samples
        q1, _, q3 = statistics.quantiles(sorted_samples, n=4, method="inclusive")

        medians.append(median)
        lower_errors.append(median - q1)
        upper_errors.append(q3 - median)

    return medians, lower_errors, upper_errors


def plot_runtime_medians(
    input_sizes: Sequence[float],
    runtime_samples: Sequence[Sequence[float]],
    *,
    x_label: str = "Input size",
    y_label: str = "Runtime",
    title: str = "Median Runtime vs Input Size",
    output_file: Optional[str] = None,
) -> None:
    """
    Plot median runtime against input size with asymmetric error bars.
    """
    medians, lower_errors, upper_errors = compute_medians_and_error_bars(
        input_sizes, runtime_samples
    )

    # matplotlib expects asymmetric y-errors as [lower_list, upper_list]
    yerr = [lower_errors, upper_errors]

    plt.figure(figsize=(8, 5))
    plt.errorbar(
        input_sizes,
        medians,
        yerr=yerr,
        fmt="-o",
        capsize=5,
    )
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")

    plt.show()


if __name__ == "__main__":
    # Example usage:
    input_sizes = [10, 20, 30, 40, 50]

    # Each inner list is repeated runtime measurements for that input size
    runtime_samples = [
        [0.12, 0.11, 0.13, 0.10, 0.14],
        [0.24, 0.23, 0.22, 0.25, 0.27],
        [0.38, 0.35, 0.41, 0.39, 0.37],
        [0.55, 0.58, 0.53, 0.57, 0.56],
        [0.80, 0.76, 0.79, 0.83, 0.78],
    ]

    plot_runtime_medians(
        input_sizes,
        runtime_samples,
        x_label="Number of cases",
        y_label="Runtime (seconds)",
        title="Median Solver Runtime vs Number of Cases",
        output_file="median_runtime_plot.png",
    )