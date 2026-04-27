# CHANGELOG — Version 23
## A Patio Adjacency Lemma for Greedy Colorings, with Computational Evidence Toward Branch-Set Connectivity
### Mizael Antonio Tovar Reyes — Ciudad Juárez, Chihuahua, México — April 2026

DOI: https://doi.org/10.5281/zenodo.19802374

---

## V20 → V23 Summary

| Version | Key change |
|---|---|
| V20 | Script 10, Case 3b (Anti-Destruction), 562 graphs verified, GAP=0 |
| V21 | **Patio Adjacency Lemma introduced** (Theorem 3.4) — main original result |
| V22 | Proof of Proposition 3.1 corrected; clear proved/open table added |
| V23 | Honest title, Proposition framing, conditional Lemma 4.4, modern references |

---

## What Changed from V20 to V23

### 1. Title and Framing

**V20 title:** "Palette-Expansion Numbers and a Constructive Proof of Hadwiger's Conjecture"

**V23 title:** "A Patio Adjacency Lemma for Greedy Colorings, with Computational Evidence Toward Branch-Set Connectivity"

**Why:** V20 claimed to prove Hadwiger's Conjecture for all k. After careful review,
the branch-set connectivity step (making all B_i simultaneously connected and pairwise
disjoint) was not fully justified for k ≥ 7. V23 is honest about this.

---

### 2. Main Result: Patio Adjacency Lemma (Theorem 3.4) — NEW in V21

**Statement:** Let G be a connected simple graph with optimal greedy palette-expansion
coloring achieving χ(G) = k, with expansion centers c₁,...,cₖ. For every pair of
colors i < j, there exists a vertex u ∈ Aᵢ such that (u, cⱼ) ∈ E(G). Consequently,
there is always a direct edge between Aᵢ and Aⱼ in G.

**Status:** PROVED mathematically + verified on 130,000+ graphs, 0 counterexamples.

**This is the genuine original contribution of this work.**

---

### 3. χ(G) = 1 + p(G) re-framed as Proposition 3.1

In V20 this was called "Theorem 4.1" and presented as a major new result.
In V23 it is correctly framed as **Proposition 3.1** — the result is essentially
folklore (equivalent to the greedy algorithm), and the novelty is the constructive
packaging via expansion centers. Computational verification: 562 graphs, 0 failures.

---

### 4. Open Problem 6.1 — Branch-Set Connectivity

**V20** claimed Hadwiger's Conjecture was fully proved.

**V23** explicitly states: *Hadwiger's Conjecture for k ≥ 7 remains OPEN.*

The missing step is:

> **Open Problem 6.1:** Prove that branch sets B₁,...,Bₖ can always be made
> simultaneously connected and pairwise disjoint for any connected simple graph G
> with χ(G) = k. This is equivalent to Hadwiger's conjecture for k ≥ 7.

Computational evidence: 562 graphs tested, GAP=0 — but no general proof yet.

---

### 5. Lemma 4.4 (Alternating Connector) — now conditional

In V20 this was called "Lemma 8.3f" and presented as unconditional.
In V23 it is **Lemma 4.4 (conditional)**: the alternating connector construction
works for the tested cases (Case A=5,417 / Case B=177 / GAP=0) but its general
proof is part of the open problem.

---

### 6. Modern References Added (V23)

- Norin, Postle & Song (2023)
- Postle (2020)
- Robertson & Seymour (Graph Minors series)

---

## Files Added in V23

| File | Description |
|---|---|
| `conjecture/Hadwiger_V23.docx` | Official paper V23 (Word) |
| `conjecture/Hadwiger_V23.pdf` | Official paper V23 (PDF) |
| `conjecture/CHANGELOG_V23.md` | This file |

## Files from V20 Retained (historical)

| File | Description |
|---|---|
| `conjecture/CHANGELOG_V20.md` | V20 changelog (historical record) |
| `conjecture/case3b_anti_destruction_proof.md` | Case 3b formal proof (still valid) |
| `conjecture/mizaeltovarreyes-chromatic-hadwiger-V20.tex` | V20 LaTeX source (historical) |

---

## What Carries Forward Unchanged from V20

- All computational results: 562 graphs, GAP=0, 10 independent scripts
- Script 10: 5/5 false-negative cases closed with explicit branch sets
- Case 3b (Anti-Destruction Theorem) — still valid, now contextualized
- All script code (scripts 1–10) — no functional changes
- Pairwise adjacency verification (130,000+ graphs, 0 failures)

---

*Mizael Antonio Tovar Reyes — Ciudad Juárez, Chihuahua, México — April 26, 2026*
