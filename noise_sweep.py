
from pathlib import Path
import csv
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
import matplotlib.pyplot as plt


# ---------------- CONFIGURATION ----------------

# Output directory
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHOTS = 5000

NOISE_LEVELS = [
    0.00,
    0.01,
    0.02,
    0.05,
    0.10,
    0.20,
]


# ---------------- QUANTUM CIRCUIT ----------------

def create_bell_circuit():
    """Prepare a Bell state and measure both qubits."""

    circuit = QuantumCircuit(2, 2)

    circuit.h(0)
    circuit.cx(0, 1)

    circuit.measure([0, 1], [0, 1])

    return circuit


# ---------------- NOISE MODEL ----------------

def create_noise_model(noise_rate):
    """Apply depolarizing errors after H and CX gates."""

    model = NoiseModel()

    h_error = depolarizing_error(noise_rate, 1)
    cx_error = depolarizing_error(noise_rate, 2)

    model.add_all_qubit_quantum_error(h_error, ["h"])
    model.add_all_qubit_quantum_error(cx_error, ["cx"])

    return model


# ---------------- SIMULATION ----------------

def simulate(noise_rate, shots):
    """Run an ideal or noisy Bell-state experiment."""

    circuit = create_bell_circuit()

    if noise_rate == 0:
        simulator = AerSimulator()
    else:
        noise_model = create_noise_model(noise_rate)
        simulator = AerSimulator(noise_model=noise_model)

    result = simulator.run(
        circuit,
        shots=shots
    ).result()

    return result.get_counts()


# ---------------- DATA ANALYSIS ----------------

def analyze_counts(counts, shots):
    """Calculate probabilities and distribution distance."""

    p00 = counts.get("00", 0) / shots
    p01 = counts.get("01", 0) / shots
    p10 = counts.get("10", 0) / shots
    p11 = counts.get("11", 0) / shots

    matching_rate = p00 + p11
    mismatch_rate = p01 + p10

    # Ideal Bell-state probabilities:
    # P(00) = 0.5, P(11) = 0.5
    # P(01) = 0,   P(10) = 0

    tvd = 0.5 * (
        abs(p00 - 0.5)
        + abs(p01)
        + abs(p10)
        + abs(p11 - 0.5)
    )

    # Correlation when measuring both qubits in Z basis.
    # Equal bits contribute +1; different bits contribute -1.
    correlation = matching_rate - mismatch_rate

    return {
        "p00": p00,
        "p01": p01,
        "p10": p10,
        "p11": p11,
        "matching_rate": matching_rate,
        "mismatch_rate": mismatch_rate,
        "correlation": correlation,
        "tvd": tvd,
    }


# ---------------- EXPERIMENT ----------------

def run_noise_sweep():
    """Run every noise level and collect experimental data."""

    rows = []

    print("\nQUANTUM NOISE SWEEP")
    print("=" * 65)

    for noise_rate in NOISE_LEVELS:
        counts = simulate(noise_rate, SHOTS)
        metrics = analyze_counts(counts, SHOTS)

        row = {
            "configured_noise_percent": noise_rate * 100,
            "shots": SHOTS,
            "count_00": counts.get("00", 0),
            "count_01": counts.get("01", 0),
            "count_10": counts.get("10", 0),
            "count_11": counts.get("11", 0),
            **{
                key: value
                for key, value in metrics.items()
            },
        }

        rows.append(row)

        print(
            f"Noise: {noise_rate:5.1%} | "
            f"Mismatch: {metrics['mismatch_rate']:6.2%} | "
            f"Correlation: {metrics['correlation']:7.4f} | "
            f"TVD: {metrics['tvd']:.4f}"
        )

    return rows


# ---------------- CSV EXPORT ----------------

def save_results(rows):
    """Export experiment results to the output folder."""

    filename = OUTPUT_DIR / "noise_results.csv"

    with filename.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults saved to: {filename}")

# ---------------- VISUALIZATION ----------------

def plot_results(rows):
    """Plot mismatch rate and correlation versus noise."""

    noise = [
        row["configured_noise_percent"]
        for row in rows
    ]

    mismatch = [
        row["mismatch_rate"] * 100
        for row in rows
    ]

    correlation = [
        row["correlation"]
        for row in rows
    ]

    distance = [
        row["tvd"]
        for row in rows
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].plot(
        noise, mismatch,
        marker="o",
        label="Observed mismatch"
    )
    axes[0].set_title("Noise vs Mismatch Rate")
    axes[0].set_xlabel("Configured gate error (%)")
    axes[0].set_ylabel("Mismatching outcomes (%)")
    axes[0].grid(True)
    axes[0].legend()

    axes[1].plot(
        noise, correlation,
        marker="o",
        label="Measured correlation"
    )
    axes[1].plot(
        noise, distance,
        marker="s",
        label="Total variation distance"
    )
    axes[1].set_title("Noise vs Quantum Statistics")
    axes[1].set_xlabel("Configured gate error (%)")
    axes[1].set_ylabel("Metric value")
    axes[1].grid(True)
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "noise_analysis.png", dpi=200)
    plt.show()


# ---------------- MAIN ----------------

def main():
    rows = run_noise_sweep()
    save_results(rows)
    plot_results(rows)

    print("\nExperiment complete.")
    print("Files created:")
    print("- noise_results.csv")
    print("- noise_analysis.png")


if __name__ == "__main__":
    main()
