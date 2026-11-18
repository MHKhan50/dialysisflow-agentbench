"""Allocation policies. Each returns a plan: patient id -> (unit, shift), unassigned patients omitted.

No policy has errors added on purpose. Infeasible plans can arise only where agents act on their own
view of a shared resource (the transport fleet), which is the coordination problem under study.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Tuple

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .network import COHORTS, Patient, Scenario

Plan = Dict[int, Tuple[str, str]]


class Ledger:
    """Remaining chairs per unit-shift and transport seats per shift."""

    def __init__(self, scenario: Scenario) -> None:
        self.chairs = dict(scenario.free_chairs)
        self.seats = dict(scenario.transport_seats)

    def fits(self, patient: Patient, unit: str, shift: str) -> bool:
        if self.chairs[(unit, shift)] < 1:
            return False
        return patient.cohort != "transport" or self.seats[shift] >= 1

    def take(self, patient: Patient, unit: str, shift: str) -> None:
        self.chairs[(unit, shift)] -= 1
        if patient.cohort == "transport":
            self.seats[shift] -= 1


def _sequential(scenario: Scenario, order: List[Patient]) -> Plan:
    ledger = Ledger(scenario)
    plan: Plan = {}
    for patient in order:
        choices = [o for o in scenario.options(patient) if ledger.fits(patient, *o)]
        if choices:
            unit, shift = min(choices, key=lambda o: (scenario.burden(patient, *o), o))
            ledger.take(patient, unit, shift)
            plan[patient.pid] = (unit, shift)
    return plan


def list_order_greedy(scenario: Scenario) -> Plan:
    """One central planner, patients in list order, each to the lowest-burden option still free."""
    return _sequential(scenario, list(scenario.patients))


def most_constrained_greedy(scenario: Scenario) -> Plan:
    """Same planner, but patients with the fewest options are placed first."""
    order = sorted(scenario.patients, key=lambda p: (len(scenario.options(p)), p.pid))
    return _sequential(scenario, order)


def _unit_offers(scenario: Scenario, waiting: List[Patient], chairs: Dict, seats_view: Callable[[str], Dict]) -> Dict:
    """Each receiving unit offers its free chairs to the waiting patients it can serve, nearest first.

    ``seats_view(unit)`` is the transport-seat count that unit believes is available.
    """
    offers: Dict[int, List[Tuple[float, str, str]]] = defaultdict(list)
    for unit in scenario.units:
        seats = dict(seats_view(unit))
        local = dict((k, v) for k, v in chairs.items() if k[0] == unit)
        candidates = []
        for patient in waiting:
            for (u, shift) in scenario.options(patient):
                if u == unit:
                    candidates.append((scenario.burden(patient, unit, shift), patient.pid, shift, patient))
        taken = set()
        for burden, pid, shift, patient in sorted(candidates, key=lambda c: (c[0], c[1], c[2])):
            if pid in taken or local[(unit, shift)] < 1:
                continue
            if patient.cohort == "transport":
                if seats[shift] < 1:
                    continue
                seats[shift] -= 1
            local[(unit, shift)] -= 1
            taken.add(pid)
            offers[pid].append((burden, unit, shift))
    return offers


def independent_units(scenario: Scenario) -> Plan:
    """One round. Every unit books transport against the whole fleet as if no other unit used it."""
    offers = _unit_offers(scenario, list(scenario.patients), dict(scenario.free_chairs),
                          lambda unit: scenario.transport_seats)
    return {pid: min(o)[1:] for pid, o in offers.items()}


def independent_units_gated(scenario: Scenario) -> Plan:
    """The same plan, checked against the shared ledger before it is committed; bookings that do not fit are dropped."""
    proposed = independent_units(scenario)
    ledger = Ledger(scenario)
    plan: Plan = {}
    by_pid = {p.pid: p for p in scenario.patients}
    for pid in sorted(proposed):
        unit, shift = proposed[pid]
        if ledger.fits(by_pid[pid], unit, shift):
            ledger.take(by_pid[pid], unit, shift)
            plan[pid] = (unit, shift)
    return plan


def _share_seats(scenario: Scenario) -> Dict[str, Dict[str, int]]:
    """Split each shift's transport seats between units in proportion to their free chairs (largest remainder)."""
    quotas: Dict[str, Dict[str, int]] = {u: {} for u in scenario.units}
    for shift, seats in scenario.transport_seats.items():
        chairs = {u: scenario.free_chairs[(u, shift)] for u in scenario.units}
        total = sum(chairs.values())
        if total == 0:
            for u in scenario.units:
                quotas[u][shift] = 0
            continue
        raw = {u: seats * chairs[u] / total for u in scenario.units}
        base = {u: int(raw[u]) for u in scenario.units}
        left = seats - sum(base.values())
        for u in sorted(scenario.units, key=lambda u: (-(raw[u] - base[u]), u))[:left]:
            base[u] += 1
        for u in scenario.units:
            quotas[u][shift] = base[u]
    return quotas


def quota_units(scenario: Scenario) -> Plan:
    """One round of separate offers, but each unit may only book its own fixed quota of transport seats."""
    quotas = _share_seats(scenario)
    offers = _unit_offers(scenario, list(scenario.patients), dict(scenario.free_chairs), lambda unit: quotas[unit])
    return {pid: min(o)[1:] for pid, o in offers.items()}


def repeated_independent_units(scenario: Scenario, max_rounds: int = 50) -> Plan:
    """Rounds of separate offers: units re-offer chairs that lapsed, but each still books transport
    against the whole fleet, because there is no shared record of seats."""
    chairs = dict(scenario.free_chairs)
    plan: Plan = {}
    waiting = list(scenario.patients)
    for _ in range(max_rounds):
        offers = _unit_offers(scenario, waiting, chairs, lambda unit: scenario.transport_seats)
        if not offers:
            break
        for pid, options in offers.items():
            _, unit, shift = min(options)
            plan[pid] = (unit, shift)
            chairs[(unit, shift)] -= 1
        waiting = [p for p in waiting if p.pid not in plan]
        if not waiting:
            break
    return plan


def coordinated_units(scenario: Scenario, max_rounds: int = 50) -> Plan:
    """Rounds of offers against a shared ledger: patients accept their best offer, units re-offer what is left."""
    ledger = Ledger(scenario)
    plan: Plan = {}
    waiting = list(scenario.patients)
    for _ in range(max_rounds):
        offers = _unit_offers(scenario, waiting, ledger.chairs, lambda unit: ledger.seats)
        if not offers:
            break
        by_pid = {p.pid: p for p in waiting}
        progress = False
        for pid in sorted(offers, key=lambda q: (min(offers[q])[0], q)):
            for burden, unit, shift in sorted(offers[pid]):
                if ledger.fits(by_pid[pid], unit, shift):
                    ledger.take(by_pid[pid], unit, shift)
                    plan[pid] = (unit, shift)
                    progress = True
                    break
        waiting = [p for p in waiting if p.pid not in plan]
        if not progress or not waiting:
            break
    return plan


def _milp_plan(scenario: Scenario, fair: bool) -> Plan:
    """Exact optimum. ``fair``: maximise the lower cohort fulfilment rate first, then the number placed,
    then minimise burden. Otherwise: maximise the number placed, then minimise burden."""
    pairs = [(p, u, s) for p in scenario.patients for (u, s) in scenario.options(p)]
    if not pairs:
        return {}
    n = len(pairs)
    cohort_size = {c: sum(p.cohort == c for p in scenario.patients) for c in COHORTS}
    present = [c for c in COHORTS if cohort_size[c] > 0]

    rows, lo, hi = [], [], []

    def add_row(coeffs: Dict[int, float], lower: float, upper: float, width: int) -> None:
        row = np.zeros(width)
        for j, v in coeffs.items():
            row[j] += v
        rows.append(row)
        lo.append(lower)
        hi.append(upper)

    def base_constraints(width: int) -> None:
        for patient in scenario.patients:
            add_row({j: 1 for j, (p, _, _) in enumerate(pairs) if p.pid == patient.pid}, 0, 1, width)
        for key, cap in scenario.free_chairs.items():
            idx = {j: 1 for j, (_, u, s) in enumerate(pairs) if (u, s) == key}
            if idx:
                add_row(idx, 0, cap, width)
        for shift, cap in scenario.transport_seats.items():
            idx = {j: 1 for j, (p, _, s) in enumerate(pairs) if s == shift and p.cohort == "transport"}
            if idx:
                add_row(idx, 0, cap, width)

    def solve(c, width, integrality, extra=None):
        nonlocal rows, lo, hi
        rows, lo, hi = [], [], []
        base_constraints(width)
        if extra:
            for coeffs, lower, upper in extra:
                add_row(coeffs, lower, upper, width)
        upper_bounds = np.ones(width)
        if width > n:
            upper_bounds[n:] = 1.0
        res = milp(c=c, constraints=LinearConstraint(np.array(rows), lo, hi), integrality=integrality,
                   bounds=Bounds(np.zeros(width), upper_bounds), options={"time_limit": 60})
        if res.status != 0 or res.x is None:
            raise RuntimeError("MILP not solved to proven optimality for %s: %s" % (scenario.scenario_id, res.message))
        return res

    extra: List = []
    if fair and len(present) > 1:
        # Stage 1: maximise t, the lowest cohort fulfilment rate (t is variable n).
        width = n + 1
        c = np.zeros(width)
        c[n] = -1
        cons = []
        for cohort in present:
            coeffs = {j: 1.0 / cohort_size[cohort] for j, (p, _, _) in enumerate(pairs) if p.cohort == cohort}
            coeffs[n] = -1.0
            cons.append((coeffs, 0.0, np.inf))
        integrality = np.r_[np.ones(n), 0]
        res = solve(c, width, integrality, cons)
        t_star = res.x[n]
        for cohort in present:
            coeffs = {j: 1.0 for j, (p, _, _) in enumerate(pairs) if p.cohort == cohort}
            extra.append((coeffs, math_ceil_safe(t_star * cohort_size[cohort]), np.inf))

    # Stage 2: maximise the number placed.
    res = solve(-np.ones(n), n, np.ones(n), extra)
    placed = round(-res.fun)
    extra.append(({j: 1.0 for j in range(n)}, placed, placed))
    # Stage 3: minimise total burden at that number placed.
    burden = np.array([scenario.burden(p, u, s) for (p, u, s) in pairs])
    res = solve(burden, n, np.ones(n), extra)
    return {p.pid: (u, s) for j, (p, u, s) in enumerate(pairs) if res.x[j] > 0.5}


def math_ceil_safe(value: float) -> float:
    """Round up, ignoring solver noise just above an integer."""
    return float(np.ceil(value - 1e-4))


def optimal_fair(scenario: Scenario) -> Plan:
    return _milp_plan(scenario, fair=True)


def optimal_throughput(scenario: Scenario) -> Plan:
    return _milp_plan(scenario, fair=False)


POLICIES: Dict[str, Callable[[Scenario], Plan]] = {
    "list_order_greedy": list_order_greedy,
    "most_constrained_greedy": most_constrained_greedy,
    "independent_units": independent_units,
    "independent_units_gated": independent_units_gated,
    "quota_units": quota_units,
    "repeated_independent_units": repeated_independent_units,
    "coordinated_units": coordinated_units,
    "optimal_throughput": optimal_throughput,
    "optimal_fair": optimal_fair,
}
