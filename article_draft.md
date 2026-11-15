# DialysisFlow-AgentBench: Evaluating Multi-Agent Coordination for Dialysis Service Disruptions

**Status:** Research protocol and benchmark prototype, v0.1.0. No empirical claims should be made until experiments have been run, analysed, and independently checked.

## Abstract

This project proposes a reproducible synthetic benchmark for evaluating operational recovery planning after haemodialysis service disruptions. It compares centralised, single-agent, uncoordinated multi-agent, and coordinated safety-gated approaches. Outcomes include session allocation, operational constraint violations, unallocated workload, delay-burden proxies, and human-review requirements. The benchmark is explicitly limited to operational simulation and does not make clinical decisions.

## Research questions

- RQ1: How do the four approaches compare on operational recovery under identical disruption scenarios?
- RQ2: Does explicit capacity reconciliation reduce operational constraint violations?
- RQ3: What is the trade-off between recovery performance and human-review escalation?
- RQ4: How sensitive are outcomes to disruption severity and resource constraints?

## Methods

The initial release contains 20 fictional scenarios and a deterministic multi-seed runner. Each scenario specifies requested sessions, available slots, staff capacity, machine capacity, disruption severity, and a synthetic priority class. Policies are evaluated on the same scenario/seed combinations.

## Limitations

The initial dataset is small and synthetic. The current fairness metric is a workload-burden proxy, not a validated equity measure. The baseline policies are deliberately transparent toy comparators, not state-of-the-art optimisers or production agents. The benchmark does not model clinical urgency, treatment prescriptions, patient outcomes, travel, infection control, or real-world staffing regulations.

## Planned next steps

Expand the scenario generator; define stronger optimisation baselines; introduce paired statistical analysis and bootstrap confidence intervals; pre-register hypotheses; conduct a systematic literature review; and obtain domain-expert review of operational assumptions.
