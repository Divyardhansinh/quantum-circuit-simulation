# Quantum Circuit Simulation and Entanglement Analysis

## Overview

This project explores quantum circuit simulation using Python, Qiskit, and Qiskit Aer. It investigates quantum superposition, measurement probabilities, Bell-state entanglement, and the effects of depolarizing noise on quantum correlations.

## Features

- Simulates basic quantum gates and measurement outcomes.
- Prepares and measures Bell states.
- Simulates depolarizing noise on single-qubit and two-qubit gates.
- Sweeps across different noise levels.
- Estimates quantum correlations in the X, Y, and Z measurement bases.
- Calculates an entanglement witness and statistical confidence bounds.
- Repeats simulations to study sampling variability.
- Saves CSV data and Matplotlib visualizations.

## Technologies

- Python
- Qiskit
- Qiskit Aer
- Matplotlib

## Getting Started

Clone this repository and navigate into the project directory.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the main experiment:

```bash
python main.py
```

Run the noise and entanglement analyses:

```bash
python noise_experiment.py
python noise_sweep.py
python entanglement_experiment.py
python threshold_refinement.py
python threshold_robustness.py
```

Generated results are saved in the `output/` directory.

## Statistical Interpretation

The Bell-state entanglement witness used in this project is

**S = CXX − CYY + CZZ**

For separable two-qubit states, this witness satisfies **S ≤ 1**. A statistically supported lower confidence bound above 1 provides evidence of entanglement under the assumptions of the model.

A result marked "not certified" does not prove that the state is separable. It means the selected measurements and confidence criterion were insufficient to certify entanglement.

The noise parameter represents the depolarizing error applied after specified gates; it is not the overall probability of circuit failure. The reported certification transition depends on the circuit, noise model, measurement settings, shot count, and statistical method. It should not be interpreted as a universal physical entanglement-breaking threshold.

## Limitations

This is a simulated study, not an experiment on physical quantum hardware. Results are subject to finite-shot sampling and the assumptions of the selected noise model.

## Future Improvements

- Compare simulations against analytical predictions.
- Explore alternative quantum noise models.
- Investigate larger circuits and different entangled states.
- Compare simulator results with real quantum hardware.

## License

A license has not yet been selected.
