
import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


# ==================================================
# CONFIGURATION
# ==================================================

SHOTS = 5000
CONFIDENCE_LEVEL = 0.95
ALPHA = 1.0 - CONFIDENCE_LEVEL

# 0%, 2.5%, 5%, ... 60%
NOISE_LEVELS = [i * 0.025 for i in range(25)]
BASES = ["X", "Y", "Z"]

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# 1. PREPARE THE BELL STATE
# ==================================================

def create_bell_circuit(basis):
    circuit = QuantumCircuit(2, 2)

    # |Phi+> = (|00> + |11>) / sqrt(2)
    circuit.h(0)
    circuit.cx(0, 1)

    # Rotate measurement basis
    if basis == "X":
        circuit.h(0)
        circuit.h(1)

    elif basis == "Y":
        circuit.sdg(0)
        circuit.sdg(1)
        circuit.h(0)
        circuit.h(1)

    elif basis != "Z":
        raise ValueError("Basis must be X, Y, or Z.")

    circuit.measure([0, 1], [0, 1])
    return circuit


# ==================================================
# 2. NOISE MODEL
# ==================================================

def create_noise_model(noise_rate):
    model = NoiseModel()

    one_qubit_error = depolarizing_error(noise_rate, 1)
    two_qubit_error = depolarizing_error(noise_rate, 2)

    model.add_all_qubit_quantum_error(
        one_qubit_error, ["h", "sdg"]
    )

    model.add_all_qubit_quantum_error(
        two_qubit_error, ["cx"]
    )

    return model


# ==================================================
# 3. SIMULATE ONE BASIS
# ==================================================

def simulate(basis, noise_rate):
    circuit = create_bell_circuit(basis)

    if noise_rate == 0:
        simulator = AerSimulator()
    else:
        simulator = AerSimulator(
            noise_model=create_noise_model(noise_rate)
        )

    result = simulator.run(
        circuit, shots=SHOTS
    ).result()

    return result.get_counts()


# ==================================================
# 4. ANALYZE MEASUREMENTS
# ==================================================

def analyze_counts(counts):
    n00 = counts.get("00", 0)
    n01 = counts.get("01", 0)
    n10 = counts.get("10", 0)
    n11 = counts.get("11", 0)

    total = sum(counts.values())

    if total == 0:
        raise ValueError("No measurement results found.")

    p00 = n00 / total
    p01 = n01 / total
    p10 = n10 / total
    p11 = n11 / total

    correlation = p00 + p11 - p01 - p10
    mismatch_rate = p01 + p10

    return {
        "shots": total,
        "count_00": n00,
        "count_01": n01,
        "count_10": n10,
        "count_11": n11,
        "p00": p00,
        "p01": p01,
        "p10": p10,
        "p11": p11,
        "correlation": correlation,
        "mismatch_rate": mismatch_rate,
    }


# ==================================================
# 5. CONSERVATIVE CONFIDENCE BOUND
# ==================================================

def calculate_confidence_radius():
    """
    Hoeffding bound for correlations in [-1, 1].

    Bonferroni correction covers every correlation
    estimate in the complete noise sweep.
    """

    number_of_estimates = len(NOISE_LEVELS) * len(BASES)

    return math.sqrt(
        2 * math.log(
            2 * number_of_estimates / ALPHA
        ) / SHOTS
    )


# ==================================================
# 6. RUN THE COMPLETE NOISE SWEEP
# ==================================================

def run_experiment():
    summary_rows = []
    detail_rows = []

    radius = calculate_confidence_radius()

    print("\nQUANTUM ENTANGLEMENT THRESHOLD ANALYZER")
    print("=" * 82)
    print(f"Shots per basis: {SHOTS}")
    print(f"Noise levels tested: {len(NOISE_LEVELS)}")
    print(f"Confidence level: {CONFIDENCE_LEVEL:.0%}")
    print(f"Simultaneous correlation radius: +/-{radius:.4f}")
    print()

    for noise_rate in NOISE_LEVELS:
        measurements = {}

        for basis in BASES:
            counts = simulate(basis, noise_rate)
            metrics = analyze_counts(counts)

            measurements[basis] = metrics

            detail_rows.append({
                "noise_parameter": noise_rate,
                "basis": basis,
                **metrics,
            })

        cxx = measurements["X"]["correlation"]
        cyy = measurements["Y"]["correlation"]
        czz = measurements["Z"]["correlation"]

        # Bell-state witness
        witness = cxx - cyy + czz

        # Conservative lower confidence bound
        lower_bound = witness - 3 * radius

        certified = lower_bound > 1.0

        summary = {
            "noise_parameter": noise_rate,
            "noise_percent": noise_rate * 100,
            "shots_per_basis": SHOTS,
            "correlation_xx": cxx,
            "correlation_yy": cyy,
            "correlation_zz": czz,
            "witness": witness,
            "confidence_level": CONFIDENCE_LEVEL,
            "correlation_radius": radius,
            "witness_lower_bound": lower_bound,
            "entanglement_certified": certified,
        }

        summary_rows.append(summary)

        status = "CERTIFIED" if certified else "NOT CERTIFIED"

        print(
            f"Noise: {noise_rate:6.1%} | "
            f"Witness: {witness:7.4f} | "
            f"Lower bound: {lower_bound:7.4f} | "
            f"{status}"
        )

    return summary_rows, detail_rows


# ==================================================
# 7. FIND THE CERTIFICATION THRESHOLD
# ==================================================

def report_threshold(rows):
    certified_rows = [
        row for row in rows
        if row["entanglement_certified"]
    ]

    failed_rows = [
        row for row in rows
        if not row["entanglement_certified"]
    ]

    print("\nTHRESHOLD ANALYSIS")
    print("=" * 60)

    if not failed_rows:
        print(
            "Entanglement remained certified at every "
            "tested noise level."
        )
        print(
            "Extend the sweep to investigate higher noise."
        )
        return

    if not certified_rows:
        print(
            "Entanglement was not certified at any "
            "tested noise level."
        )
        print(
            "Try lower noise levels or more measurement shots."
        )
        return

    first_failure = failed_rows[0]
    previous_levels = [
        row for row in certified_rows
        if row["noise_parameter"]
        < first_failure["noise_parameter"]
    ]

    if previous_levels:
        last_certified = previous_levels[-1]

        print(
            "Last certified grid point: "
            f"{last_certified['noise_percent']:.2f}%"
        )

    print(
        "First uncertified grid point: "
        f"{first_failure['noise_percent']:.2f}%"
    )

    print(
        "Its witness lower bound: "
        f"{first_failure['witness_lower_bound']:.4f}"
    )

    print(
        "\nThis is a grid-based estimate, not an exact "
        "physical entanglement-breaking threshold."
    )


# ==================================================
# 8. SAVE CSV FILES
# ==================================================

def save_csv(rows, filename):
    if not rows:
        return

    path = OUTPUT_DIR / filename

    with path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved: {path}")


# ==================================================
# 9. PLOT THE RESULTS
# ==================================================

def plot_results(rows):
    noise = [row["noise_percent"] for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Correlations
    for key, label in [
        ("correlation_xx", "XX correlation"),
        ("correlation_yy", "YY correlation"),
        ("correlation_zz", "ZZ correlation"),
    ]:
        axes[0].plot(
            noise,
            [row[key] for row in rows],
            marker="o",
            markersize=3,
            label=label,
        )

    axes[0].axhline(0, linestyle="--", linewidth=1)
    axes[0].set_title("Correlations vs Gate Noise")
    axes[0].set_xlabel("Configured gate noise parameter (%)")
    axes[0].set_ylabel("Correlation")
    axes[0].set_ylim(-1.1, 1.1)
    axes[0].grid(True)
    axes[0].legend()

    # Witness
    witness = [row["witness"] for row in rows]
    lower = [row["witness_lower_bound"] for row in rows]

    axes[1].plot(
        noise, witness, marker="o",
        markersize=3, label="Measured witness"
    )

    axes[1].plot(
        noise, lower, marker="s",
        markersize=3, label="95% lower confidence bound"
    )

    axes[1].axhline(
        1, linestyle="--", label="Entanglement threshold"
    )

    axes[1].set_title("Entanglement Certification vs Noise")
    axes[1].set_xlabel("Configured gate noise parameter (%)")
    axes[1].set_ylabel("Witness value")
    axes[1].grid(True)
    axes[1].legend()

    plt.tight_layout()

    path = OUTPUT_DIR / "entanglement_threshold_analysis.png"
    plt.savefig(path, dpi=200)
    print(f"Saved: {path}")

    plt.show()


# ==================================================
# 10. MAIN
# ==================================================

def main():
    summary_rows, detail_rows = run_experiment()

    save_csv(
        summary_rows,
        "entanglement_threshold_summary.csv"
    )

    save_csv(
        detail_rows,
        "entanglement_threshold_details.csv"
    )

    report_threshold(summary_rows)
    plot_results(summary_rows)

    print("\nExperiment complete.")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
