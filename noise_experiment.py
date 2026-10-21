
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt


SHOTS = 5000
ERROR_RATE = 0.05


def create_bell_circuit():
    """Create an entangled two-qubit Bell-state circuit."""

    circuit = QuantumCircuit(2, 2)

    circuit.h(0)
    circuit.cx(0, 1)

    circuit.measure([0, 1], [0, 1])

    return circuit


def create_noise_model(error_rate):
    """Model depolarizing noise after H and CNOT gates."""

    noise_model = NoiseModel()

    # One-qubit depolarizing error after a Hadamard gate.
    one_qubit_error = depolarizing_error(error_rate, 1)

    # Two-qubit depolarizing error after a CNOT gate.
    two_qubit_error = depolarizing_error(error_rate, 2)

    noise_model.add_all_qubit_quantum_error(
        one_qubit_error, ["h"]
    )

    noise_model.add_all_qubit_quantum_error(
        two_qubit_error, ["cx"]
    )

    return noise_model


def run_simulation(circuit, noise_model=None):
    """Run the circuit and return measurement counts."""

    simulator = AerSimulator(noise_model=noise_model)

    result = simulator.run(
        circuit,
        shots=SHOTS
    ).result()

    return result.get_counts()


def probability_distribution(counts):
    """Convert measurement counts into probabilities."""

    total = sum(counts.values())

    return {
        outcome: count / total
        for outcome, count in counts.items()
    }


def total_variation_distance(counts, expected):
    """Compare measured and expected probability distributions."""

    observed = probability_distribution(counts)

    outcomes = set(observed) | set(expected)

    return 0.5 * sum(
        abs(observed.get(outcome, 0.0)
            - expected.get(outcome, 0.0))
        for outcome in outcomes
    )


def analyze_results(label, counts):
    """Print probabilities and Bell-state correlations."""

    print(f"\n--- {label} ---")
    print("Counts:", counts)

    distribution = probability_distribution(counts)

    for outcome in sorted(["00", "01", "10", "11"]):
        probability = distribution.get(outcome, 0.0)
        print(f"{outcome}: {probability * 100:.2f}%")

    total = sum(counts.values())

    # For this Bell state, matching bits are 00 and 11.
    matching = counts.get("00", 0) + counts.get("11", 0)
    mismatching = counts.get("01", 0) + counts.get("10", 0)

    print(f"Matching outcomes (00/11): {matching / total:.2%}")
    print(f"Mismatching outcomes (01/10): {mismatching / total:.2%}")


def main():
    circuit = create_bell_circuit()

    print("Bell-State Circuit:")
    print(circuit.draw())

    # Ideal simulation: no noise model.
    ideal_counts = run_simulation(circuit)

    # Noisy simulation: depolarizing errors after selected gates.
    noise_model = create_noise_model(ERROR_RATE)
    noisy_counts = run_simulation(circuit, noise_model)

    # Ideal Bell state has equal probabilities for 00 and 11.
    theoretical_distribution = {
        "00": 0.5,
        "01": 0.0,
        "10": 0.0,
        "11": 0.5,
    }

    analyze_results("IDEAL SIMULATION", ideal_counts)
    analyze_results("NOISY SIMULATION", noisy_counts)

    ideal_distance = total_variation_distance(
        ideal_counts, theoretical_distribution
    )

    noisy_distance = total_variation_distance(
        noisy_counts, theoretical_distribution
    )

    print("\n--- Comparison with Ideal Bell-State Theory ---")
    print(f"Ideal distance: {ideal_distance:.4f}")
    print(f"Noisy distance: {noisy_distance:.4f}")
    print(f"Configured gate error rate: {ERROR_RATE:.1%}")

    # Compare both distributions in one histogram.
    plot_histogram(
        [ideal_counts, noisy_counts],
        legend=["Ideal", "Noisy"],
        title="Ideal vs Noisy Bell-State Simulation"
    )

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
