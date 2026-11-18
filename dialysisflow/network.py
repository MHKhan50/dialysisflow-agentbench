"""Seeded synthetic dialysis networks with one disrupted unit.

The model is operational only: chairs, shifts, travel time and a shared transport fleet. It holds no
clinical information and makes no clinical decisions.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

SHIFTS: Tuple[str, ...] = ("MWF-AM", "MWF-PM", "TTS-AM", "TTS-PM")
COHORTS: Tuple[str, ...] = ("transport", "independent")

# Travel limits in minutes; a patient who needs transport has the tighter limit.
TRAVEL_LIMIT = {"transport": 45.0, "independent": 75.0}
# Extra burden, in minutes-equivalent, when a patient moves from morning to afternoon or back.
TIME_CHANGE_PENALTY = 20.0

SCARCITY_LEVELS: Dict[str, Tuple[float, float]] = {
    # Share of chairs already occupied at the receiving units, sampled per unit and shift.
    "low": (0.60, 0.75),
    "medium": (0.75, 0.85),
    "high": (0.85, 0.95),
}
SEVERITY_LEVELS: Dict[str, int] = {"partial": 2, "full": 4}  # shifts closed at the disrupted unit


@dataclass(frozen=True)
class Patient:
    pid: int
    shift: str
    cohort: str
    location: Tuple[float, float]


@dataclass
class Scenario:
    scenario_id: str
    scarcity: str
    severity: str
    units: List[str]
    unit_location: Dict[str, Tuple[float, float]]
    free_chairs: Dict[Tuple[str, str], int]
    transport_seats: Dict[str, int]
    patients: List[Patient]
    travel: Dict[Tuple[int, str], float] = field(default_factory=dict)

    def options(self, patient: Patient) -> List[Tuple[str, str]]:
        """Unit-shift pairs that keep the weekday pattern and respect the patient's travel limit."""
        pattern = patient.shift.split("-")[0]
        limit = TRAVEL_LIMIT[patient.cohort]
        out = []
        for unit in self.units:
            if self.travel[(patient.pid, unit)] > limit:
                continue
            for shift in SHIFTS:
                if shift.startswith(pattern):
                    out.append((unit, shift))
        return out

    def burden(self, patient: Patient, unit: str, shift: str) -> float:
        change = TIME_CHANGE_PENALTY if shift != patient.shift else 0.0
        return self.travel[(patient.pid, unit)] + change


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def make_scenario(seed: int, scarcity: str, severity: str) -> Scenario:
    """Build one network. Every random draw comes from ``seed``, so a scenario is fully reproducible."""
    rng = random.Random(seed)
    n_receiving = rng.randint(4, 6)
    units = ["U%d" % (i + 1) for i in range(n_receiving)]
    closed_location = (20.0, 20.0)
    unit_location = {}
    for unit in units:
        angle = rng.uniform(0, 2 * math.pi)
        radius = rng.uniform(8.0, 30.0)
        unit_location[unit] = (20.0 + radius * math.cos(angle), 20.0 + radius * math.sin(angle))

    low, high = SCARCITY_LEVELS[scarcity]
    free_chairs = {}
    for unit in units:
        chairs = rng.randint(8, 16)
        for shift in SHIFTS:
            occupied = round(rng.uniform(low, high) * chairs)
            free_chairs[(unit, shift)] = max(0, chairs - occupied)

    closed_shifts = list(SHIFTS) if SEVERITY_LEVELS[severity] == 4 else rng.sample(list(SHIFTS), 2)
    patients: List[Patient] = []
    closed_chairs = rng.randint(10, 16)
    for shift in SHIFTS:
        if shift not in closed_shifts:
            continue
        for _ in range(round(rng.uniform(0.8, 1.0) * closed_chairs)):
            cohort = "transport" if rng.random() < 0.35 else "independent"
            location = (closed_location[0] + rng.gauss(0, 8.0), closed_location[1] + rng.gauss(0, 8.0))
            patients.append(Patient(len(patients), shift, cohort, location))

    n_transport = sum(p.cohort == "transport" for p in patients)
    # Spare seats in the shared patient-transport fleet, per shift, for the whole network.
    transport_seats = {s: max(1, round(rng.uniform(0.6, 1.0) * n_transport / len(closed_shifts))) for s in SHIFTS}

    scenario = Scenario("S%05d" % seed, scarcity, severity, units, unit_location, free_chairs,
                        transport_seats, patients)
    for patient in patients:
        for unit in units:
            # Road travel approximated as 1.5 minutes per km plus 5 minutes of fixed time.
            scenario.travel[(patient.pid, unit)] = round(5.0 + 1.5 * _distance(patient.location, unit_location[unit]), 1)
    return scenario


def make_suite(n_per_cell: int, base_seed: int = 1000) -> List[Scenario]:
    """Scenarios for every scarcity and severity level; seeds never repeat across cells."""
    suite = []
    seed = base_seed
    for scarcity in SCARCITY_LEVELS:
        for severity in SEVERITY_LEVELS:
            for _ in range(n_per_cell):
                suite.append(make_scenario(seed, scarcity, severity))
                seed += 1
    return suite
