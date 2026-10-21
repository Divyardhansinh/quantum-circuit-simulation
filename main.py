
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt


# -----------------------------------------------
# QUANTUM SIMULATOR
# -----------------------------------------------

simulator = AerSimulator()


def build_circuit(experiment):
    """Create a quantum circuit for the selected experiment."""

    if experiment == 1:
        # Experiment 1: Qubit without any gate
        circuit = QuantumCircuit(1, 1)
        circuit.measure(0, 0)
        expected = {"0": 1.0}

    elif experiment == 2:
        # Experiment 2: Create superposition
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.measure(0, 0)
        expected = {"0": 0.5, "1": 0.5}

    elif experiment == 3:
        # Experiment 3: Apply H twice
        circuit = QuantumCircuit(1, 1)
        circuit.h(0)
        circuit.h(0)
        circuit.measure(0, 0)
        expected = {"0": 1.0}

    elif experiment == 4:
        # Experiment 4: Create a Bell state
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        expected = {"00": 0.5, "11": 0.5}

    else:
        raise ValueError("Unknown experiment.")

    return circuit, expected


def calculate_statistics(counts, expected, shots):
    """Compare observed outcomes with theoretical probabilities."""

    print("\n--- Measurement Statistics ---")

    all_outcomes = sorted(set(counts) | set(expected))

    total_variation = 0.0

    for outcome in all_outcomes:
        observed_count = counts.get(outcome, 0)
        observed_probability = observed_count / shots
        expected_probability = expected.get(outcome, 0.0)

        difference = abs(
            observed_probability - expected_probability
        )
        total_variation += difference

        print(
            f"Outcome {outcome}: "
            f"Count = {observed_count:4d} | "
            f"Observed = {observed_probability * 100:6.2f}% | "
            f"Expected = {expected_probability * 100:6.2f}%"
        )

    # Total variation distance ranges from 0 to 1.
    total_variation /= 2

    print(
        "\nTotal variation distance: "
        f"{total_variation:.4f}"
    )
    print(
        "Smaller values indicate a closer match "
        "to the theoretical distribution."
    )


def run_experiment(experiment, shots):
    """Run, analyze, and plot a quantum experiment."""

    circuit, expected = build_circuit(experiment)

    print("\n" + "=" * 45)
    print(f"Running Experiment {experiment}")
    print("=" * 45)

    print("\nQuantum Circuit:")
    print(circuit.draw())

    # Execute the circuit on the simulator.
    result = simulator.run(
        circuit,
        shots=shots
    ).result()

    counts = result.get_counts()

    print("\nRaw Measurement Counts:")
    print(counts)

    calculate_statistics(counts, expected, shots)

    # Show the measurement distribution.
    plot_histogram(
        counts,
        title=f"Experiment {experiment}: {shots} Shots"
    )
    plt.tight_layout()
    plt.show()


def show_menu():
    """Display available experiments."""

    print("\n===== QUANTUM COMPUTING LAB =====")
    print("1. Qubit without a gate")
    print("2. Superposition using Hadamard")
    print("3. Quantum interference using H twice")
    print("4. Two-qubit entanglement (Bell state)")
    print("5. Run all experiments")
    print("0. Exit")


def get_shots():
    """Ask the user for a valid number of shots."""

    while True:
        try:
            shots = int(input("Enter number of shots (100-10000): "))

            if 100 <= shots <= 10000:
                return shots

            print("Please enter a number between 100 and 10000.")

        except ValueError:
            print("Invalid input. Enter a whole number.")


def main():
    """Main application loop."""

    while True:
        show_menu()

        try:
            choice = int(input("\nSelect an experiment: "))
        except ValueError:
            print("Invalid choice. Please enter a number.")
            continue

        if choice == 0:
            print("Thank you for using Quantum Computing Lab!")
            break

        if choice not in range(1, 6):
            print("Choose an option from 0 to 5.")
            continue

        shots = get_shots()

        if choice == 5:
            for experiment in range(1, 5):
                run_experiment(experiment, shots)
        else:
            run_experiment(choice, shots)


if __name__ == "__main__":
    main()
