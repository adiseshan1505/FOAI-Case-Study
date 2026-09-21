# Infodemic Containment

**Misinformation spreaders vs. fact-checking moderators on a social network.**
A multi-agent adversarial simulation for the Foundations of AI (FOAI) case study.

![Type](https://img.shields.io/badge/type-multi--agent%20simulation-1f4e79)
![Agents](https://img.shields.io/badge/agent%20types-2-1f4e79)
![Status](https://img.shields.io/badge/status-design%20phase-orange)

---

## Table of Contents

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
- [Planned Repository Layout](#planned-repository-layout)
- [Project Status](#project-status)
- [References](#references)

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
| Total exposure | Area under the infection curve |
| Peak infection | Maximum number of simultaneously exposed nodes |
| Time-to-containment | Rounds until spread is contained |
| False-positive rate | Share of takedowns applied to true content |
| Post-shock recovery time | Rounds to regain containment after the bot-swarm shock |

## Scope and Assumptions

- Claims are **synthetic predicates**. There is no NLP and no real-world content.
- The simulator **holds ground truth**. Moderators receive only noisy evidence,
  and this asymmetry is what makes the environment partially observable.
- Graph structure is **static** apart from node state changes and sockpuppet
  creation.
- The knowledge base is **small and hand-authored**, so results characterize the
  *decision strategy*, not real-world fact-checking accuracy.

## Planned Repository Layout

> The code below does not exist yet. This is the intended structure.

```text
FOAI-Case-Study/
├── README.md
├── Infodemic_Containment_Problem_Statement.pdf   # Original problem statement
├── Infodemic_Containment_Problem_Statement.docx
├── src/
│   ├── env/            # Scale-free graph, node states, Independent Cascade dynamics
│   ├── agents/
│   │   ├── spreader/   # Random and centrality-informed seeding, sockpuppets
│   │   └── moderator/  # Random, FIFO, and impact-weighted policies
│   ├── kb/             # Hand-authored knowledge base and Horn-clause inference
│   ├── shock/          # Coordinated bot-swarm scenario
│   └── metrics/        # Exposure, peak, containment, false positives, recovery
├── experiments/        # C1–C6 configs, λ sweep, seed lists
├── results/            # Raw run outputs and aggregated tables/plots
└── report/             # Write-up and figures
```

## Project Status

| Milestone | Status |
|---|---|
| Problem statement and design | Done |
| Environment (graph + Independent Cascade) | Planned |
| Knowledge base and Horn-clause inference | Planned |
| Spreader and moderator policies | Planned |
| Bot-swarm shock scenario | Planned |
| C1–C6 experiments and λ sweep | Planned |
| Analysis and report | Planned |

## References

- Vosoughi, S., Roy, D., & Aral, S. (2018). The spread of true and false news
  online. *Science*, 359(6380), 1146–1151.
- Kempe, D., Kleinberg, J., & Tardos, É. (2003). Maximizing the spread of
  influence through a social network. *Proceedings of KDD 2003*.
- Barabási, A.-L., & Albert, R. (1999). Emergence of scaling in random networks.
  *Science*, 286(5439), 509–512.
