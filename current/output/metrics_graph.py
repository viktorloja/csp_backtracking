import matplotlib.pyplot as plt

def plot_graphs(results, file_path):
        
    solvers = list(results.keys())
    scores = [metrics["score"] for metrics in results.values()]
    runtimes = [metrics["runtime"] for metrics in results.values()]
    memories = [metrics["memory"] for metrics in results.values()]

    fig, axes = plt.subplots(3, 1, figsize=(8, 10))

    bars = axes[0].bar(solvers, scores)
    axes[0].bar_label(bars)
    axes[0].set_title("Scores across Solvers")
    axes[0].set_xlabel("Solver")
    axes[0].set_ylabel("Score")

    bars = axes[1].bar(solvers, runtimes)
    axes[0].bar_label(bars)
    axes[1].set_title("Runtimes across Solvers")
    axes[1].set_xlabel("Solver")
    axes[1].set_ylabel("Runtime")

    bars = axes[2].bar(solvers, memories)
    axes[2].bar_label(bars)
    axes[2].set_title("Memory Usage across Solvers")
    axes[2].set_xlabel("Solver")
    axes[2].set_ylabel("Memory Usage")

    plt.tight_layout()
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.show()
    print("Graph saved to:", file_path)
