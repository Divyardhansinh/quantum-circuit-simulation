from pathlib import Path
import math
import csv

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


# ==========================================
# EXPERIMENT SETTINGS
# ==========================================

SHOTS = 10_000
ALPHA = 0.05

# Focus on the transition found in the first sweep:
# 24.00%, 24.25%, ..., 29.00%
NOISE_LEVELS = [
    (24 + i * 0.25) / 100
    for i in range(21)
]

BASES = ["X", "Y", "Z"]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "threshold_refinement_summary.csv"
DETAILS_FILE = OUTPUT_DIR / "threshold_refinement_details.csv"
PLOT_FILE = OUTPUT_DIR / "threshold_refinement.png"


# ==========================================
# NOISE MODEL
# ==========================================

def create_noise_model(noise_level):
    """Create depolarizing errors for one- and two-qubit gates."""

    noise_model = NoiseModel()

    error_1q = depolarizing_error(noise_level, 1)
    error_2q = depolarizing_error(noise_level, 2)

    noise_model.add_all_qubit_quantum_error(
        error_1q, ["h", "sdg"]
    )

    noise_model.add_all_qubit_quantum_error(
        error_2q, ["cx"]
    )

    return noise_model


# ==========================================
# BELL-STATE MEASUREMENT CIRCUITS
# ==========================================

def create_bell_circuit(basis):
    """Prepare a Bell state and measure a chosen correlation."""

    circuit = QuantumCircuit(2, 2)

    # Prepare |Phi+> = (|00> + |11>) / sqrt(2)
    circuit.h(0)
    circuit.cx(0, 1)

    # Rotate both qubits into the requested measurement basis.
    if basis == "X":
        circuit.h(0)
        circuit.h(1)

    elif basis == "Y":
        circuit.sdg(0)
        circuit.h(0)

        circuit.sdg(1)
        circuit.h(1)

    elif basis == "Z":
        pass

    else:
        raise ValueError(f"Unknown measurement basis: {basis}")

    circuit.measure([0, 1], [0, 1])

    return circuit


# ==========================================
# CORRELATION AND CONFIDENCE CALCULATIONS
# ==========================================

def calculate_correlation(counts):
    """
    Calculate correlation from two-qubit measurement counts.

    Equal bits (00, 11) contribute +1.
    Different bits (01, 10) contribute -1.
    """

    same = counts.get("00", 0) + counts.get("11", 0)
    different = counts.get("01", 0) + counts.get("10", 0)

    total = same + different

    if total == 0:
        raise ValueError("No measurement results were returned.")

    return (same - different) / total


def calculate_confidence_radius(number_of_estimates):
    """
    Hoeffding bound with a Bonferroni correction.

    Covers all correlation estimates in the focused sweep
    simultaneously with confidence of at least 1 - ALPHA.
    """

    return math.sqrt(
        2 * math.log(
            2 * number_of_estimates / ALPHA
        ) / SHOTS
    )


# ==========================================
# RUN THE REFINEMENT SWEEP
# ==========================================

def run_refinement():
    print("=" * 58)
    print("ENTANGLEMENT THRESHOLD REFINEMENT")
    print("=" * 58)

    number_of_estimates = len(NOISE_LEVELS) * len(BASES)

    radius = calculate_confidence_radius(number_of_estimates)

    print(f"Shots per basis: {SHOTS:,}")
    print(f"Noise levels: {len(NOISE_LEVELS)}")
    print(
        f"Noise range: {NOISE_LEVELS[0] * 100:.2f}% "
        f"to {NOISE_LEVELS[-1] * 100:.2f}%"
    )
    print(f"Step size: 0.25 percentage points")
    print(f"Confidence level: {(1 - ALPHA) * 100:.0f}%")
    print(f"Simultaneous correlation radius: +/-{radius:.4f}")
    print()

    summary_rows = []
    detail_rows = []

    for noise_level in NOISE_LEVELS:
        noise_model = create_noise_model(noise_level)
        simulator = AerSimulator(noise_model=noise_model)

        circuits = [
            create_bell_circuit(basis)
            for basis in BASES
        ]

        compiled_circuits = transpile(
            circuits,
            simulator,
            optimization_level=0
        )

        results = simulator.run(
            compiled_circuits,
            shots=SHOTS
        ).result()

        correlations = {}

        for index, basis in enumerate(BASES):
            counts = results.get_counts(index)
            correlation = calculate_correlation(counts)

            correlations[basis] = correlation

            detail_rows.append({
                "noise_percent": noise_level * 100,
                "basis": basis,
                "shots": SHOTS,
                "correlation": correlation,
                "confidence_radius": radius,
            })

        # Entanglement witness for the Bell state.
        witness = (
            correlations["X"]
            - correlations["Y"]
            + correlations["Z"]
        )

        # Conservative lower confidence bound.
        witness_lower_bound = witness - 3 * radius

        certified = witness_lower_bound > 1.0

        summary_rows.append({
            "noise_percent": noise_level * 100,
            "CXX": correlations["X"],
            "CYY": correlations["Y"],
            "CZZ": correlations["Z"],
            "witness": witness,
            "witness_lower_bound": witness_lower_bound,
            "confidence_radius": radius,
            "certified_entangled": certified,
        })

        status = "CERTIFIED" if certified else "NOT CERTIFIED"

        print(
            f"Noise: {noise_level * 100:5.2f}% | "
            f"Witness: {witness:7.4f} | "
            f"Lower bound: {witness_lower_bound:7.4f} | "
            f"{status}"
        )

    # ======================================
    # SAVE CSV FILES
    # ======================================

    with SUMMARY_FILE.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=summary_rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    with DETAILS_FILE.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=detail_rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(detail_rows)

    # ======================================
    # FIND THE CERTIFICATION TRANSITION
    # ======================================

    certified_rows = [
        row for row in summary_rows
        if row["certified_entangled"]
    ]

    uncertified_rows = [
        row for row in summary_rows
        if not row["certified_entangled"]
    ]

    print("\n" + "=" * 58)
    print("REFINEMENT RESULTS")
    print("=" * 58)

    if certified_rows:
        last_certified = max(
            certified_rows,
            key=lambda row: row["noise_percent"]
        )

        print(
            "Last certified point in this range: "
            f"{last_certified['noise_percent']:.2f}%"
        )
    else:
        print("No points in this range were certified.")

    if uncertified_rows:
        first_uncertified = min(
            uncertified_rows,
            key=lambda row: row["noise_percent"]
        )

        print(
            "First uncertified point in this range: "
            f"{first_uncertified['noise_percent']:.2f}%"
        )

    # ======================================
    # PLOT RESULTS
    # ======================================

    noise_percent = [
        row["noise_percent"] for row in summary_rows
    ]

    witness_values = [
        row["witness"] for row in summary_rows
    ]

    lower_bounds = [
        row["witness_lower_bound"] for row in summary_rows
    ]

    plt.figure(figsize=(10, 6))

    plt.plot(
        noise_percent,
        witness_values,
        marker="o",
        label="Entanglement witness"
    )

    plt.plot(
        noise_percent,
        lower_bounds,
        marker="s",
        linestyle="--",
        label="95% simultaneous lower bound"
    )

    plt.axhline(
        y=1.0,
        linestyle=":",
        label="Separable-state threshold (1)"
    )

    plt.xlabel("Depolarizing noise parameter (%)")
    plt.ylabel("Witness value")
    plt.title("Refined Entanglement Certification Threshold")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300)
    plt.close()

    print(f"\nSaved: {SUMMARY_FILE}")
    print(f"Saved: {DETAILS_FILE}")
    print(f"Saved: {PLOT_FILE}")
    print("\nRefinement complete.")


if __name__ == "__main__":
    run_refinement()