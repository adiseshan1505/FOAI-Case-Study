# Infodemic Containment

**Misinformation spreaders vs. fact-checking moderators on a social network.**
A multi-agent adversarial simulation for the Foundations of AI (FOAI) case study.

![Type](https://img.shields.io/badge/type-multi--agent%20simulation-1f4e79)
![Agents](https://img.shields.io/badge/agent%20types-2-1f4e79)
![Status](https://img.shields.io/badge/status-working%20prototype-2e7d32)

---

## Table of Contents

- [Quickstart](#quickstart)
- [Overview](#overview)
- [The Problem](#the-problem)
- [Agents](#agents)
- [Environment](#environment)
- [Decision Problems](#decision-problems)
- [Objectives and the λ Trade-off](#objectives-and-the-λ-trade-off)
- [Stress Scenario: Bot-Swarm Shock](#stress-scenario-bot-swarm-shock)
- [Research Questions and Hypotheses](#research-questions-and-hypotheses)
- [Evaluation Plan](#evaluation-plan)
- [Scope and Assumptions](#scope-and-assumptions)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Repository Layout](#repository-layout)
- [How It Is Modeled](#how-it-is-modeled)
- [Results](#results)
- [Limitations](#limitations)
- [Project Status](#project-status)
- [References](#references)

---

## Quickstart

Requires Python 3.10 or newer. From the repository root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                    
python experiments/run_matrix.py          # then open results/matrix_exposure.png
```

Three more runners cover the rest of the study: `run_shock.py` (bot-swarm
shock), `run_lambda_sweep.py` (the λ trade-off), and `run_sensitivity.py`
(robustness to the default settings). All charts and CSV tables are
written to `results/`. See [Getting Started](#getting-started) for flags and
configuration.

---

## Overview

False stories spread farther and faster than true ones, largely because a small
number of well-connected accounts amplify them. Verification does not scale the
same way: fact-checking is slow, evidence-dependent, and limited by reviewer
capacity. Over-aggressive takedowns also have a cost, because wrongly suppressing
true content erodes user trust.

The result is a **race between propagation speed and verification capacity**,
played out on a network where influence is very unevenly distributed.

This project models that race as a two-player, mixed-motive simulation and asks
where informed search and resource-aware prioritization beat uninformed baselines
in an adversarial, partially observable setting. It also shows how a rule-based
knowledge representation layer fits into a larger agent decision loop.

## The Problem

> Given a social network, a stream of claims (some true, some false, with labels
> hidden from moderators), and a fixed per-round verification budget, how should a
> moderator decide **which claims to verify, when, and what action to take**, in
> order to **minimize total misinformation exposure while limiting wrongful
> takedowns**, against an adversary that actively adapts its spreading strategy?

Three difficulties are built in:

| Difficulty | What it means here |
|---|---|
| **Incomplete information** | Moderators never see ground truth. They infer it from claim content, propagation velocity, and source credibility history. |
| **Scarce resources** | Only `B` claims can be checked per round, so every check has an opportunity cost. |
| **Adaptive opponent** | The spreader observes moderator behavior and changes tactics, so a fixed policy gets exploited. |

A single-agent search or optimization framing fails because the environment
contains another goal-directed agent whose actions change the outcome of yours.

## Agents

There are exactly **two agent types**. Ordinary users are *not* agents. They are
passive nodes that reshare probabilistically.

|  | Spreader Agent | Moderator Agent |
|---|---|---|
| **Goal** | Maximize exposed nodes before containment | Minimize total exposure + λ · false-positive takedowns |
| **Actions** | Post, reshare, create sockpuppets, target hubs | Flag, quarantine / rate-limit, publish counter-claim, escalate |
| **Percepts** | Local engagement, visible moderator activity | Claim content, propagation velocity, source credibility history |
| **Constraint** | Limited posts and accounts per round | Verification budget `B` per round, detection delay |

## Environment

The environment is a **scale-free graph** `G = (V, E)` of roughly **500 to 1000
nodes**. Scale-free structure is used because real social networks have
heavy-tailed degree distributions with a few very influential hubs.

- **Node states:** `clean`, `exposed`, `quarantined`
- **Edge weights:** reshare probability `p(u, v)`, modulated by a trust score
- **Claims:** synthetic predicates with hidden true/false labels, checkable
  against a knowledge base
- **Dynamics:** Independent Cascade. Each newly exposed node gets one chance to
  pass the claim to each neighbor with probability `p(u, v)`

| Property | Justification |
|---|---|
| Partially observable | Moderators infer truth from evidence; spreaders do not know the exact detection threshold |
| Stochastic | User resharing is probabilistic (Independent Cascade Model) |
| Multi-agent, mixed-motive | Adversarial goals, with neutral bystander nodes reacting probabilistically in between |
| Dynamic | The network state changes between an agent's turns |
| Sequential | Containment decisions now change what the spreader can do later |

## Decision Problems

### Spreader

1. **Where to seed the claim:** a random node or a high-centrality hub?
2. **When to deploy sockpuppets,** and how to react to visible moderator activity?

### Moderator

1. **Which claims deserve the `B` checks this round?** Ranking uses estimated
   impact (*propagation velocity × reach of current carriers*) rather than
   arrival order.
2. **How to verify?** Claims are represented as predicates and matched against a
   knowledge base using **Horn-clause rule-based inference**.
3. **What to do when the knowledge base cannot resolve a claim?** Escalate,
   rate-limit provisionally, or ignore. This is where the limits of knowledge
   representation show up honestly.

## Objectives and the λ Trade-off

- **Spreader:** maximize `E[exposed nodes at horizon T]`
- **Moderator:** minimize `Total Exposure + λ · FalsePositives`

The parameter **λ** controls the moderator's caution:

| λ | Moderator behavior | Consequence |
|---|---|---|
| Low | Aggressive | Contains rumors fast, but wrongly suppresses true content |
| High | Cautious | Avoids collateral damage, but lets rumors run longer |

Sweeping λ and reporting the resulting **exposure vs. false-positive frontier**
is a key analytical result of this project.

## Stress Scenario: Bot-Swarm Shock

At a scheduled round, many spreader instances activate simultaneously, mimicking
a breaking-news panic. This tests whether the moderator's policy is robust or
only works on the happy path. The moderator is expected to **re-prioritize under
load** rather than continue with its pre-shock queue.

## Research Questions and Hypotheses

| ID | Statement |
|---|---|
| **RQ1** | How much does informed play beat uninformed play for each side? |
| **H1** | Centrality-targeted spreading reaches significantly more nodes than random targeting at equal post budget. |
| **H2** | Impact-weighted moderation beats FIFO and random moderation on total exposure at equal `B`. |
| **RQ2** | How does the system behave under the bot-swarm shock? |
| **H3** | An adaptive moderator recovers containment within `k` rounds, while a static policy does not. |
| **RQ3** | How does λ shape the exposure vs. false-positive trade-off? |

## Evaluation Plan

A **2 × 3 experiment matrix** (six conditions), run over **multiple random
seeds per condition** because the process is stochastic.

| Spreader \ Moderator | Random | FIFO | Impact-weighted |
|---|---|---|---|
| **Random targeting** | C1 | C2 | C3 |
| **Centrality-informed** | C4 | C5 | C6 |

How the matrix maps to the hypotheses:

- **H1:** compare rows within a column (e.g. C1 vs. C4).
- **H2:** compare columns within a row (e.g. C4 vs. C6).
- **H3:** apply the shock in each condition and compare recovery.
- **RQ3:** sweep λ on the moderator side.

### Metrics (per run)

| Metric | Description |
|---|---|
| Total exposure | Area under the infection curve, i.e. users exposed to false claims summed over all rounds |
| Peak infection | Largest number of users newly exposed to false claims in a single round |
| Time-to-containment | Rounds until new false exposures stay at or below a threshold (default 2 per round); reported as the horizon if never reached |
| False-positive rate | Share of takedowns applied to true content |
| Post-shock recovery time | Rounds after the shock round until new false exposures settle back at or below the threshold |

## Scope and Assumptions

- Claims are **synthetic predicates**. There is no NLP and no real-world content.
- The simulator **holds ground truth**. Moderators receive only noisy evidence,
  and this asymmetry is what makes the environment partially observable.
- Graph structure is **static** apart from node state changes and sockpuppet
  creation.
- The knowledge base is **small and hand-authored**, so results characterize the
  *decision strategy*, not real-world fact-checking accuracy.

## Tech Stack

| Area | Choice | Used for |
|---|---|---|
| Language | Python 3.10+ (developed on 3.14) | Entire simulator, agents, and experiment runners |
| Graph | [NetworkX](https://networkx.org/) | Scale-free graph generation (Barabási–Albert) and degree centrality |
| Numerics | [NumPy](https://numpy.org/) | Seeded random number generation for reproducible runs, and vectorized metric calculations |
| Data handling | [pandas](https://pandas.pydata.org/) | Collecting per-round logs and aggregating results across seeds and conditions |
| Plotting | [Matplotlib](https://matplotlib.org/) | Infection curves, the λ exposure vs. false-positive frontier, and shock recovery plots |
| Configuration | [PyYAML](https://pyyaml.org/) | Experiment configs for the C1–C6 conditions and the λ sweep |
| Testing | [pytest](https://docs.pytest.org/) | Unit tests for cascade dynamics, inference, and policies |
| Knowledge base | Custom pure-Python Horn-clause engine | Hand-authored facts and rules queried by backward chaining, kept in-house so the inference stays transparent |

Design choices:

- **No agent framework or ML library.** Both agents use explicit, inspectable
  policies, which keeps the comparison between strategies clean.
- **Reproducibility.** Every run takes an explicit seed, and each experiment
  condition is repeated over a fixed list of seeds.
- **Dependencies** are declared in `pyproject.toml` and mirrored in
  `requirements.txt`.

## Getting Started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest                                   # unit and simulation tests

python experiments/run_matrix.py         # C1-C6 matrix (H1, H2)
python experiments/run_shock.py          # bot-swarm shock in every condition (H3)
python experiments/run_lambda_sweep.py   # exposure vs. false-positive frontier (RQ3)
python experiments/run_sensitivity.py    # does H2 survive other budgets, KB coverage, adaptation? (~1.5 min)
```

Each runner writes CSV tables and a PNG chart to `results/`. Useful flags:

| Flag | Applies to | Effect |
|---|---|---|
| `--seeds N` | all runners | Use seeds `0..N-1` instead of the config's seed list. Pair it with `--out`, or the committed charts in `results/` are overwritten |
| `--config PATH` | all runners | Use a different config (default `experiments/configs/default.yaml`) |
| `--out DIR` | all runners | Write results somewhere other than `results/` |
| `--with-pure-impact` | `run_matrix.py` | Add a ranking by velocity × reach alone, without the suspicion weighting |
| `--param NAME` | `run_sensitivity.py` | Sweep one parameter (`moderator.budget_per_round`, `moderator.kb_coverage`, or `spreader.max_sockpuppets`) instead of all three |
| `--values 1,2,4` | `run_sensitivity.py` | Values to try for `--param` |
| `--k N` | `run_shock.py` | Rounds allowed for recovery in the H3 check (default 15) |
| `--with-static` | `run_shock.py` | Add an ablation whose impact ranking is frozen when a claim is first seen |
| `--condition C6` | `run_lambda_sweep.py` | Which condition to sweep |
| `--lams 0,1,10,100` | `run_lambda_sweep.py` | The λ values to try |

For a quick look that leaves the committed results untouched, run for example
`python experiments/run_matrix.py --seeds 5 --out /tmp/demo`.

All parameters (graph size, budget `B`, λ, shock size, KB coverage, and so on)
live in `experiments/configs/default.yaml`.

## Repository Layout

```text
FOAI-Case-Study/
├── README.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── docs/
│   ├── Infodemic_Containment_Problem_Statement.pdf
│   └── Infodemic_Containment_Problem_Statement.docx
├── src/
│   └── infodemic/
│       ├── __init__.py
│       ├── config.py
│       ├── metrics.py
│       ├── env/
│       │   ├── __init__.py
│       │   ├── network.py
│       │   ├── cascade.py
│       │   ├── claims.py
│       │   └── simulation.py
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── spreader.py
│       │   └── moderator.py
│       ├── policies/
│       │   ├── __init__.py
│       │   ├── spreader_policies.py
│       │   └── moderator_policies.py
│       ├── kb/
│       │   ├── __init__.py
│       │   ├── facts.py
│       │   ├── rules.py
│       │   └── inference.py
│       └── scenarios/
│           ├── __init__.py
│           └── bot_swarm.py
├── experiments/
│   ├── configs/
│   │   ├── default.yaml
│   │   └── conditions.yaml
│   ├── common.py
│   ├── run_matrix.py
│   ├── run_lambda_sweep.py
│   ├── run_sensitivity.py
│   └── run_shock.py
├── tests/
│   ├── test_cascade.py
│   ├── test_inference.py
│   ├── test_policies.py
│   └── test_simulation.py
├── results/
└── report/
```

| Path | Responsibility |
|---|---|
| `src/infodemic/env/` | Scale-free graph, node states, claims with hidden labels, Independent Cascade dynamics, and the round-by-round simulation loop |
| `src/infodemic/agents/` | The two agent types: spreader (post, reshare, sockpuppets) and moderator (flag, verify, quarantine, rate-limit, escalate) |
| `src/infodemic/policies/` | Swappable strategies: random and centrality-informed seeding; random, FIFO, and impact-weighted moderation |
| `src/infodemic/kb/` | Hand-authored facts and rules, and Horn-clause inference for verifying claims |
| `src/infodemic/scenarios/` | The coordinated bot-swarm shock |
| `src/infodemic/metrics.py` | Total exposure, peak infection, time-to-containment, false-positive rate, post-shock recovery time |
| `experiments/` | Configs, shared helpers (`common.py`), and runners for the C1–C6 matrix, the shock runs, the λ sweep, and the sensitivity sweeps |
| `tests/` | Unit tests for the cascade, inference, policies, metrics, config, and full simulation runs |
| `results/` | Generated charts and summary tables. Raw per-run CSVs (`*_runs.csv`) are gitignored; the runners recreate them |
| `report/` | `Infodemic_Project_Walkthrough.pdf`, a walkthrough of what the project does, how it was built and how the code works. A formal write-up has not been started |

## How It Is Modeled

**Round order.** Each round is one Independent Cascade hop per claim. In order:
spreaders act, organic claims arrive, the moderator acts, then every claim
spreads one hop.

**Claims and the knowledge base.** Claims are predicates over a synthetic world
of countries, capitals, regions, and blocs (`capital_of`, `located_in`,
`allied`). The moderator's knowledge base holds a random 70% of the world's base
facts plus hand-written Horn rules, and answers by backward chaining with a
`TRUE`, `FALSE`, or `UNKNOWN` verdict. Negative knowledge uses rules such as
`not_capital_of(X, C) :- capital_of(X, D), neq(C, D)`. The knowledge base is
sound but incomplete: it never gives a wrong verdict, and about 40% of claims
come back `UNKNOWN`. False positives therefore come only from acting on
unresolved claims.

**What the moderator sees.** A claim view with no hidden label: a noisy content
score, propagation velocity (users exposed in the last hop), reach (summed degree
of current carriers), and a per-source credibility ledger built from past
verdicts. These are combined into an estimated probability that the claim is
false.

**Moderator decisions.**
- *Selection:* `random`, `fifo`, or `impact_weighted`. Impact is velocity × reach,
  multiplied by the estimated probability of falsehood so that checks are not
  spent on likely-true claims. Two ablations are available: `impact_only` ranks by
  velocity × reach alone, as the problem statement words it, and `impact_static`
  freezes the score when a claim is first seen, which isolates re-ranking from
  impact scoring in the shock runs.
- *Verified false:* quarantine, which halts spread. A separate counter-claim
  action is not modeled.
- *Unresolved:* under the default `adaptive` rule the moderator rate-limits
  provisionally when `p_false × expected next-hop exposure × lookahead × (1 −
  rate_limit_factor) > λ × (1 − p_false)`, and escalates to a slow, capacity-limited
  human review (95% accurate) when the potential harm is high enough. Rate-limiting
  scales reshare probability by `rate_limit_factor`. This is where λ acts.
- *Cost of an error:* a claim counts as a false positive if it was ever
  rate-limited or quarantined while true, even if a later review released it.

**Spreader.** Each spreader seeds false claims at random nodes or at hubs (top 5%
by degree centrality). It sees only the public log of suppressions. If one of its
own claims was suppressed in the last three rounds, it deploys sockpuppets and has
them reshare its strongest live claim, while continuing to seed its own posts as
before. Sockpuppets are extra nodes linked to accounts chosen by the same
targeting policy; they carry claims but are never counted as exposed users.
Setting `spreader.max_sockpuppets: 0` turns the adaptation off, which is how its
effect is measured. An earlier version made the spreader post from sockpuppets
instead of seeding, which hurt the centrality-informed spreader; the current
design was chosen so that adapting never costs the spreader its own seeding.

**Bot-swarm shock.** At the shock round, `num_spreaders` extra non-adaptive
spreaders post simultaneously for `duration` rounds, using the same targeting
policy as the row being tested. The main spreader's campaign ends before the
shock, so containment can be reached first and recovery measured against an
absolute threshold.

**Reproducibility.** Each component draws from its own seeded random stream. A
given seed produces the same graph, knowledge base, and organic claims in every
condition, so comparisons are paired by seed and confidence intervals come from a
paired bootstrap.

## Results

Default config, 30 seeds per condition. The moderator's budget `B = 2` and the
spreader's 3 posts per round were chosen so that verification is scarce; the
[sensitivity analysis](#sensitivity-analysis) below shows how much the H2 result
depends on that choice. Full tables are in `results/`.

### H1 and H2: informed play vs. uninformed play

![Total exposure by targeting and moderation policy](results/matrix_exposure.png)

| Spreader \ Moderator | Random | FIFO | Impact-weighted |
|---|---|---|---|
| **Random targeting** | C1: 466 | C2: 507 | C3: 253 |
| **Centrality-informed** | C4: 1073 | C5: 1209 | C6: 442 |

Mean total exposure. Differences below are paired by seed, with 95% bootstrap
confidence intervals.

| Hypothesis | Comparison | Mean difference | 95% CI | Supported |
|---|---|---|---|---|
| H1 | Centrality − random targeting, random moderator | +607 | [554, 663] | Yes |
| H1 | Centrality − random targeting, FIFO moderator | +702 | [643, 762] | Yes |
| H1 | Centrality − random targeting, impact-weighted moderator | +189 | [152, 229] | Yes |
| H2 | FIFO − impact-weighted, random spreader | +254 | [202, 308] | Yes |
| H2 | Random − impact-weighted, random spreader | +213 | [168, 266] | Yes |
| H2 | FIFO − impact-weighted, centrality spreader | +767 | [707, 825] | Yes |
| H2 | Random − impact-weighted, centrality spreader | +631 | [580, 683] | Yes |

Hub targeting helps the spreader against every moderator, but the impact-weighted
moderator cuts that advantage from roughly 600 to 700 extra exposures down to 189.

Ranking by velocity × reach alone, without the suspicion weighting, gives almost
the same result (C3p: 283, C6p: 443, against 253 and 442), and still beats FIFO by
+223 [171, 279] and +766 [699, 830]. So H2 does not depend on the suspicion
weighting added on top of the problem statement's ranking.

### H3: bot-swarm shock

![Incidence of false exposures around the bot-swarm shock](results/shock_recovery.png)

| Condition | Total exposure | Mean recovery (rounds) | Recovered within 15 rounds |
|---|---|---|---|
| C1 random / random | 1195 | 17.8 | 43% |
| C2 random / FIFO | 1321 | 18.1 | 37% |
| C3 random / impact-weighted | 606 | 10.8 | 83% |
| C4 centrality / random | 3321 | 18.9 | 20% |
| C5 centrality / FIFO | 3593 | 20.3 | 7% |
| C6 centrality / impact-weighted | 2010 | 13.3 | 83% |

Recovery is faster with the impact-weighted moderator, by 5.6 to 7.3 rounds
against FIFO and random (all four 95% CIs exclude zero). Nearly all runs
(93% or more) eventually recover, so the difference is speed, not whether the
system recovers at all. In the `--with-static` ablation, freezing the impact
ranking costs 2.6 rounds against random targeting (CI [0.07, 5.0], only just
excluding zero) and 5.4 against centrality targeting. Against the centrality
spreader the frozen ranking recovers about as slowly as FIFO and random
(18.7 rounds, against 20.3 and 18.9), so re-ranking under load is what
carries the benefit there.

### RQ3: the λ trade-off

![Exposure vs. false-positive frontier](results/lambda_frontier.png)

Condition C6, no shock.

| λ | Total exposure | False positives per run | False-positive rate |
|---|---|---|---|
| 0 | 374 | 7.73 | 12.9% |
| 1 | 378 | 3.80 | 6.8% |
| 5 | 417 | 1.50 | 2.8% |
| 10 | 442 | 1.17 | 2.3% |
| 50 | 567 | 0.20 | 0.4% |
| 200 | 651 | 0.27 | 0.6% |

The frontier is steep on the cautious side and flat on the aggressive side.
Lowering λ from 200 to 10 cuts exposure by about 209 for roughly 0.9 extra false
positives per run, while going from 5 to 0 cuts only about 43 more for about 6
extra. Most of the benefit of aggression is captured by moderate λ.

The false-positive rate does not reach zero at very high λ. That floor (about
0.27 per run) comes from the 5% error rate of human review: with review accuracy
set to 1.0, false positives at λ = 200 drop to 0.00.

### Sensitivity analysis

`run_sensitivity.py` repeats all six conditions while varying one setting at a
time. H2 (impact-weighted beats both FIFO and random) is supported in 24 of the
28 settings tested. The four failures are all at a large budget.

| Budget `B` | FIFO − impact-weighted, random spreader | FIFO − impact-weighted, centrality spreader | H2 |
|---|---|---|---|
| 1 | +274 | +692 | Holds |
| 2 (default) | +254 | +767 | Holds |
| 3 | +111 | +417 | Holds |
| 5 | +4.4 | +2.3 | Not supported |
| 8 | +2.5 | +4.1 | Not supported |

![Sensitivity to the verification budget](results/sensitivity_budget_per_round.png)

Prioritization only matters while verification is scarce. During the campaign
about four claims arrive per round (three from the spreader, about one organic),
so once `B` reaches 5 every policy can check nearly everything and they converge. H2 holds at every knowledge-base coverage tested (0.3 to 0.9)
and every sockpuppet cap tested (0 to 20). The adaptation effect can be read
straight off the sockpuppet sweep: the adaptive spreader (10 sockpuppets) causes
56 to 114 more exposures than the fixed one (0 sockpuppets), depending on the
condition.

## Limitations

- **No dataset is used, by design.** The problem statement specifies synthetic
  predicates, a generated scale-free graph, and a small hand-authored knowledge
  base. Results characterize the decision strategies, not real-world fact-checking
  accuracy or real platform behavior.
- **Hand-set parameters.** Reshare probability, claim arrival rate, evidence
  noise, the weights that turn evidence into a probability of falsehood, and the
  moderator's lookahead are fixed choices. Only λ, the budget, KB coverage, and
  the sockpuppet cap have been swept.
- **One graph family.** Every run uses a 750-node Barabási–Albert graph. Other
  sizes and real network topologies have not been tried.
- **Simplified actions.** Counter-claims are not a separate action, and the
  spreader does not mix in true claims to build credibility.
- **Fixed seeds.** Seeds 0 to 29 are fixed, so every result is exactly
  reproducible. The confidence intervals reflect variation across those 30 graphs
  and claim streams.

## Project Status

| Milestone | Status |
|---|---|
| Problem statement and design | Done |
| Environment (graph + Independent Cascade) | Done |
| Knowledge base and Horn-clause inference | Done |
| Spreader and moderator policies | Done |
| Bot-swarm shock scenario | Done |
| C1–C6 experiments and λ sweep | Done |
| Sensitivity analysis (budget `B`, KB coverage, sockpuppet cap) | Done; graph size and reshare probability not swept |
| Analysis and report | Not started |

## References

- Vosoughi, S., Roy, D., & Aral, S. (2018). The spread of true and false news
  online. *Science*, 359(6380), 1146–1151.
- Kempe, D., Kleinberg, J., & Tardos, É. (2003). Maximizing the spread of
  influence through a social network. *Proceedings of KDD 2003*.
- Barabási, A.-L., & Albert, R. (1999). Emergence of scaling in random networks.
  *Science*, 286(5439), 509–512.
