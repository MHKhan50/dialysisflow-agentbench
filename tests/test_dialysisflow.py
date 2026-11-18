from dialysisflow.evaluate import score
from dialysisflow.network import TRAVEL_LIMIT, make_scenario, make_suite
from dialysisflow.policies import POLICIES, independent_units


def test_scenarios_are_reproducible():
    a, b = make_scenario(42, "high", "full"), make_scenario(42, "high", "full")
    assert a.patients == b.patients and a.free_chairs == b.free_chairs and a.travel == b.travel


def test_suite_seeds_do_not_repeat():
    ids = [s.scenario_id for s in make_suite(3)]
    assert len(ids) == len(set(ids)) == 18


def test_options_respect_pattern_and_travel_limit():
    s = make_scenario(7, "medium", "full")
    for p in s.patients:
        for unit, shift in s.options(p):
            assert shift.split("-")[0] == p.shift.split("-")[0]
            assert s.travel[(p.pid, unit)] <= TRAVEL_LIMIT[p.cohort]


UNCOORDINATED = {"independent_units", "repeated_independent_units"}


def test_policies_with_a_shared_record_or_quota_are_feasible():
    for seed in range(1000, 1012):
        for scarcity in ("low", "high"):
            s = make_scenario(seed, scarcity, "full")
            for name, policy in POLICIES.items():
                if name not in UNCOORDINATED:
                    assert score(s, policy(s))["feasible"] == 1.0, (name, seed)


def test_optimum_places_at_least_as_many_as_any_feasible_policy():
    for seed in range(2000, 2010):
        s = make_scenario(seed, "high", "full")
        best = score(s, POLICIES["optimal_throughput"](s))["fulfilment"]
        for name, policy in POLICIES.items():
            r = score(s, policy(s))
            if r["feasible"]:
                assert r["fulfilment"] <= best + 1e-9, name


def test_fair_optimum_has_highest_lowest_cohort_rate():
    for seed in range(3000, 3010):
        s = make_scenario(seed, "high", "full")
        fair = score(s, POLICIES["optimal_fair"](s))
        floor = 1 - max(fair["unmet_transport"], fair["unmet_independent"])
        for name, policy in POLICIES.items():
            r = score(s, policy(s))
            if r["feasible"]:
                assert 1 - max(r["unmet_transport"], r["unmet_independent"]) <= floor + 1e-9, name


def test_overbooking_is_counted_not_repaired():
    found = 0
    for seed in range(1000, 1100):
        s = make_scenario(seed, "low", "partial")
        r = score(s, independent_units(s))
        found += r["transport_overbooked"] > 0
        assert r["feasible"] == float(r["transport_overbooked"] == 0)
    assert found > 0


def test_quota_never_exceeds_the_fleet():
    from dialysisflow.policies import _share_seats
    for seed in range(1000, 1050):
        s = make_scenario(seed, "medium", "partial")
        quotas = _share_seats(s)
        for shift, seats in s.transport_seats.items():
            assert sum(quotas[u][shift] for u in s.units) == seats


def test_default_sweep_settings_reproduce_the_main_scenarios():
    a = make_scenario(1234, "high", "full")
    b = make_scenario(1234, "high", "full", transport_share=0.35, fleet_factor=1.0)
    assert a.patients == b.patients and a.transport_seats == b.transport_seats
