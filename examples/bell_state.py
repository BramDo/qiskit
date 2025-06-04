"""Example script to simulate a Bell state using Qiskit."""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer
from qiskit.visualization import plot_histogram


def main() -> None:
    """Build and simulate a Bell state circuit."""
    qc = QuantumCircuit(2, 2)

    # Add a Hadamard gate on qubit 0, putting this qubit in superposition
    qc.h(0)
    # Add a CX (CNOT) gate on control qubit 0 and target qubit 1, creating entanglement
    qc.cx(0, 1)

    # Map the quantum measurement to the classical bits
    qc.measure([0, 1], [0, 1])

    backend = Aer.get_backend("aer_simulator")
    compiled_circuit = transpile(qc, backend)
    job = backend.run(compiled_circuit, shots=1024)
    result = job.result()
    counts = result.get_counts(compiled_circuit)
    print("Total count for 00 and 11 are:", counts)
    plot_histogram(counts, title="Bell state counts").show()


if __name__ == "__main__":
    main()
