
from pathlib import Path
import csv
import math
import statistics

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


# ==========================================
# EXPERIMENT SETTINGS
# ==========================================

SHOTS_PER_TRIAL = 10_000
REPEATS = 5
ALPHA = 0.05

# Focused scan around the previously observed transition.
NOISE_LEVELS = [(24 + i * 0.25) / 100 for i in range(21)]
BASES = ["X", "Y", "Z"]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_FILE = OUTPUT_DIR / "threshold_robustness_summary.csv"
DETAILS_FILE = OUTPUT_DIR / "threshold_robustness_trials.csv"
PLOT_FILE = OUTPUT_DIR / "threshold_robustness.png"


# ==========================================
# NOISE MODEL
# ==========================================

def create_noise_model(p):
    model = NoiseModel()
    model.add_all_qubit_quantum_error(
        depolarizing_error(p, 1), ["h", "sdg"]
    )
    model.add_all_qubit_quantum_error(
        depolarizing_error(p, 2), ["cx"]
    )
    return model


# ==========================================
# CIRCUITS
# ==========================================

def create_bell_circuit(basis):
    circuit = QuantumCircuit(2, 2)

    # Prepare the Bell state |Phi+>.
    circuit.h(0)
    circuit.cx(0, 1)

    if basis == "X":
        circuit.h(0)
        circuit.h(1)

    elif basis == "Y":
        circuit.sdg(0)
        circuit.h(0)
        circuit.sdg(1)
        circuit.h(1)

    elif basis != "Z":
        raise ValueError(f"Unknown basis: {basis}")

    circuit.measure([0, 1], [0, 1])
    return circuit


# ==========================================
# STATISTICS
# ==========================================

def calculate_correlation(counts):
    same = counts.get("00", 0) + counts.get("11", 0)
    different = counts.get("01", 0) + counts.get("10", 0)
    total = same + different

    if total == 0:
        raise ValueError("No measurement results received.")

    return (same - different) / total


def calculate_witness(correlations):
    # Bell-state witness: S = CXX - CYY + CZZ.
    return (
        correlations["X"]
        - correlations["Y"]
        + correlations["Z"]
    )


def calculate_confidence_radius(total_shots, number_of_estimates):
    # Hoeffding bound with Bonferroni correction.
    return math.sqrt(
        2 * math.log(2 * number_of_estimates / ALPHA)
        / total_shots
    )


def save_csv(path, rows):
    if not rows:
        return

    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ==========================================
# MAIN EXPERIMENT
# ==========================================

def run_experiment():
    print("=" * 65)
    print("ROBUST ENTANGLEMENT THRESHOLD ANALYSIS")
    print("=" * 65)

    total_shots = SHOTS_PER_TRIAL * REPEATS
    number_of_estimates = len(NOISE_LEVELS) * len(BASES)

    radius = calculate_confidence_radius(
        total_shots, number_of_estimates
    )

    print(f"Noise levels: {len(NOISE_LEVELS)}")
    print(f"Independent trials per level: {REPEATS}")
    print(f"Shots per basis per trial: {SHOTS_PER_TRIAL:,}")
    print(f"Total shots per basis per level: {total_shots:,}")
    print(f"Simultaneous confidence level: {(1 - ALPHA) * 100:.0f}%")
    print(f"Correlation confidence radius: +/-{radius:.4f}")
    print()

    summary_rows = []
    trial_rows = []

    for level_index, p in enumerate(NOISE_LEVELS):
        simulator = AerSimulator(noise_model=create_noise_model(p))

        circuits = [create_bell_circuit(b) for b in BASES]
        compiled = transpile(
            circuits, simulator, optimization_level=0
        )

        aggregate_counts = {
            basis: {"00": 0, "01": 0, "10": 0, "11": 0}
            for basis in BASES
        }

        trial_witnesses = []

        for trial in range(REPEATS):
            result = simulator.run(
                compiled,
                shots=SHOTS_PER_TRIAL
            ).result()

            trial_correlations = {}

            for circuit_index, basis in enumerate(BASES):
                counts = result.get_counts(circuit_index)

                for bitstring, count in counts.items():
                    aggregate_counts[basis][bitstring] = (
                        aggregate_counts[basis].get(bitstring, 0)
                        + count
                    )

                correlation = calculate_correlation(counts)
                trial_correlations[basis] = correlation

            trial_witness = calculate_witness(trial_correlations)
            trial_witnesses.append(trial_witness)

            trial_rows.append({
                "noise_percent": round(p * 100, 2),
                "trial": trial + 1,
                "CXX": trial_correlations["X"],
                "CYY": trial_correlations["Y"],
                "CZZ": trial_correlations["Z"],
                "witness": trial_witness,
                "shots_per_basis": SHOTS_PER_TRIAL,
            })

        # Pool counts across independent trials.
        pooled_correlations = {
            basis: calculate_correlation(aggregate_counts[basis])
            for basis in BASES
        }

        pooled_witness = calculate_witness(pooled_correlations)
        lower_bound = pooled_witness - 3 * radius
        certified = lower_bound > 1.0

        trial_mean = statistics.mean(trial_witnesses)
        trial_sd = statistics.stdev(trial_witnesses)

        summary_rows.append({
            "noise_percent": round(p * 100, 2),
            "CXX_pooled": pooled_correlations["X"],
            "CYY_pooled": pooled_correlations["Y"],
            "CZZ_pooled": pooled_correlations["Z"],
            "witness_pooled": pooled_witness,
            "trial_witness_mean": trial_mean,
            "trial_witness_sd": trial_sd,
            "confidence_radius": radius,
            "witness_lower_bound": lower_bound,
            "certified_entangled": certified,
        })

        status = "CERTIFIED" if certified else "NOT CERTIFIED"

        print(
            f"Noise: {p * 100:5.2f}% | "
            f"Witness: {pooled_witness:7.4f} | "
            f"Trial SD: {trial_sd:.4f} | "
            f"Lower bound: {lower_bound:7.4f} | {status}"
        )

    # ======================================
    # SAVE RESULTS
    # ======================================

    save_csv(SUMMARY_FILE, summary_rows)
    save_csv(DETAILS_FILE, trial_rows)

    # ======================================
    # THRESHOLD SUMMARY
    # ======================================

    print("\n" + "=" * 65)
    print("THRESHOLD SUMMARY")
    print("=" * 65)

    first_uncertified = next(
        (i for i, row in enumerate(summary_rows)
         if not row["certified_entangled"]),
        None
    )

    if first_uncertified is None:
        print("Every tested point was certified.")
    else:
        row = summary_rows[first_uncertified]
        print(
            "First uncertified point: "
            f"{row['noise_percent']:.2f}%"
        )

        sustained_index = next(
            (
                i for i in range(first_uncertified, len(summary_rows))
                if all(
                    not later["certified_entangled"]
                    for later in summary_rows[i:]
                )
            ),
            None
        )

        if sustained_index is None:
            print(
                "No sustained transition was found within this range."
            )
        else:
            sustained = summary_rows[sustained_index]
            print(
                "First point after which all remaining tested "
                "points are uncertified: "
                f"{sustained['noise_percent']:.2f}%"
            )

        if first_uncertified > 0:
            previous = summary_rows[first_uncertified - 1]
            print(
                "Immediately preceding point: "
                f"{previous['noise_percent']:.2f}% "
                f"({'CERTIFIED' if previous['certified_entangled'] else 'NOT CERTIFIED'})"
            )

    print(
        "\nThese are grid-based certification results, "
        "not an exact physical entanglement-breaking threshold."
    )

    # ======================================
    # PLOT
    # ======================================

    noise = [r["noise_percent"] for r in summary_rows]
    witness = [r["witness_pooled"] for r in summary_rows]
    lower = [r["witness_lower_bound"] for r in summary_rows]
    sd = [r["trial_witness_sd"] for r in summary_rows]

    plt.figure(figsize=(11, 6))

    plt.plot(noise, witness, marker="o", label="Pooled witness")
    plt.plot(
        noise, lower, marker="s", linestyle="--",
        label="95% simultaneous lower bound"
    )
    plt.axhline(
        1.0, linestyle=":",
        label="Separable-state threshold"
    )

    # Show the observed variation between repeated trials.
    plt.fill_between(
        noise,
        [w - s for w, s in zip(witness, sd)],
        [w + s for w, s in zip(witness, sd)],
        alpha=0.15,
        label="Pooled witness +/- trial SD"
    )

    plt.xlabel("Depolarizing noise parameter (%)")
    plt.ylabel("Entanglement witness")
    plt.title("Repeated-Trial Entanglement Threshold Analysis")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=300)
    plt.close()

    print(f"\nSaved: {SUMMARY_FILE}")
    print(f"Saved: {DETAILS_FILE}")
    print(f"Saved: {PLOT_FILE}")
    print("\nAnalysis complete.")


if __name__ == "__main__":
    run_experiment()
