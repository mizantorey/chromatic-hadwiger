# A Patio Adjacency Lemma for Greedy Colorings — V23
### by Mizael Antonio Tovar Reyes — Ciudad Juárez, Chihuahua, México

---

## What This Is

This repository contains the computational verification and mathematical results
associated with the following paper:

> **"A Patio Adjacency Lemma for Greedy Colorings, with Computational Evidence
> Toward Branch-Set Connectivity"**
> — Mizael Antonio Tovar Reyes, April 2026

The central new result is:

> **Theorem 3.4 (Patio Adjacency Lemma):** Let G be a connected simple graph
> with optimal greedy palette-expansion coloring achieving χ(G) = k, with
> expansion centers c₁,...,cₖ. For every pair of colors i < j, there exists a
> vertex u ∈ Aᵢ such that (u, cⱼ) ∈ E(G). Consequently, there is always a
> direct edge between Aᵢ and Aⱼ in G.

The approach is based on:

> **χ(G) = 1 + p(G)**  (Proposition 3.1)

where p(G) is the **palette expansion** of G. This characterization is essentially
folklore; the novelty is the constructive packaging via expansion centers.

**Hadwiger's conjecture for k ≥ 7 remains open.** The open problem (connectivity
of branch sets when F(0) = ∅) is stated precisely as Open Problem 6.1.

---

## Key Contributions

| Result | Status | Script |
|---|---|---|
| Proposition 3.1: χ(G) = 1 + p(G) | VERIFIED — 562 graphs, 0 failures, 129.3 min | matr_chromatic_identity |
| Lemma 2: Chromatic Completeness | VERIFIED — 562 graphs, 0 failures | matr_completeness_lemma |
| **Theorem 3.4: Patio Adjacency Lemma** ★ | **PROVED + VERIFIED — 130,000+ graphs, 0 failures** | matr_hadwiger_theorem |
| Exact Graph Families | VERIFIED — 66/66 families | matr_exact_families |
| Lemma 8.3d: Distributed Absorption | VERIFIED — 562 graphs, 0 failures | matr_branch_absorption |
| Lemma 4.4: Alternating Connector (conditional) | VERIFIED — Case A=5417, Case B=177, GAP=0 | matr_alternating_connector |
| K_k Minor Completeness | VERIFIED — 562 graphs, 0 failures | matr_minor_certificate |
| Hadwiger high-chi solver | 562 graphs tested | matr_high_chi_solver |
| Judge/Verifier (Lemmas 8.3c–f) | PRODUCTION READY | matr_final_verifier |
| V20: 5 false-negatives closed | PROVED — 5/5, 0 counterexamples | matr_false_negative_closer |
| **Open Problem 6.1: Branch-set connectivity** | **OPEN — k ≥ 7** | — |

★ The Patio Adjacency Lemma is the main original contribution of this work.

---

## Repository Structure

```
mizaeltovarreyes-chromatic-hadwiger/
|
+-- scripts/
|   +-- core_utils.py                     Shared library: graph generation, coloring, logging
|   +-- matr_chromatic_identity.py        Proposition 3.1: chi(G) = 1 + p(G)
|   +-- matr_completeness_lemma.py        Lemma 2: Chromatic Completeness
|   +-- matr_hadwiger_theorem.py          Theorem 3.4 + gap detection
|   +-- matr_exact_families.py            Exact graph families
|   +-- matr_branch_absorption.py         Lemma 8.3d: Distributed absorption
|   +-- matr_alternating_connector.py     Lemma 4.4: Alternating connector (conditional)
|   +-- matr_minor_certificate.py         K_k minor completeness
|   +-- matr_high_chi_solver.py           Main Hadwiger solver (chi >= 5)
|   +-- matr_final_verifier.py            Independent judge/verifier
|   +-- matr_false_negative_closer.py     V20: Proves 5 false-negative cases
|   +-- matr_full_verification.py         Full verification harness
|
+-- logs/
|   +-- log_matr_chromatic_identity.txt       500+ graphs, 129.3 min, 0 failures
|   +-- log_matr_completeness_lemma.txt       5000+ pairs, 0 failures
|   +-- log_matr_hadwiger_theorem.txt         Gap detection / Patio Lemma results
|   +-- log_matr_exact_families.txt           66/66 families verified
|   +-- log_matr_branch_absorption.txt        Absorption results
|   +-- log_matr_minor_certificate.txt        Minor certificate results
|   +-- log_matr_high_chi_solver.txt          High-chi solver results
|   +-- log_matr_final_verifier.txt           Final verifier results
|   +-- log_matr_false_negative_closer.txt    5 cases closed
|   +-- log_matr_gap_detector.txt             Gap detector results
|   +-- log_matr_high_chi_solver_detail.txt   Detailed chi=7/8 log
|   +-- log_matr_final_verifier_83*_detail.txt  Detailed lemma logs
|
+-- conjecture/
|   +-- Hadwiger_V23.docx                      Official paper (Word) — V23
|   +-- case3b_anti_destruction_proof.md       Case 3b formal proof (V20)
|   +-- Explained Simply.txt                   Non-technical explanation
|   +-- CHANGELOG_V20.md                       What changed in V20
|
+-- visual/
|   +-- INDEX.html                   Visual suite landing page (open in browser)
|   +-- 01_origin_the_drawing.html   The hand-drawn sketch that started everything
|   +-- 02_palette_expansion.html    Interactive chi = 1 + p(G) demo
|   +-- 03_chromatic_completeness.html  Lemma 2 animated proof
|   +-- 04_branch_sets_minor.html    Branch sets and K_k minor
|   +-- 05_three_phases.html         Construction: three phases
|   +-- 06_purple_connector.html     Lemma 4.4 alternating connector
|   +-- 07_proof_chain.html          Complete proof chain (clickable)
|   +-- Image1.png                   Original hand-drawn sketch
|
+-- requirements.txt
+-- LICENSE
+-- README.md
```

---

## Installation

```bash
pip install -r requirements.txt
```

For GPU acceleration (optional, requires NVIDIA GPU + CUDA 12):
```bash
pip install cupy-cuda12x
```

---

## Running the Verification

Run scripts in order from the `scripts/` directory:

```bash
cd scripts

# Step 1 — Verify chi(G) = 1 + p(G)
python matr_chromatic_identity.py

# Step 2 — Verify Lemma 2 (Chromatic Completeness)
python matr_completeness_lemma.py

# Step 3 — Theorem 3.4 (Patio Adjacency Lemma) + gap detection
python matr_hadwiger_theorem.py

# Step 4 — Exact graph families
python matr_exact_families.py

# Step 5 — Lemma 8.3d (Distributed Absorption)
python matr_branch_absorption.py

# Step 6 — Lemma 4.4 (Alternating Connector)
python matr_alternating_connector.py

# Step 7 — K_k Minor Completeness
python matr_minor_certificate.py

# Step 8 — High-chi Hadwiger solver (chi >= 5)
python matr_high_chi_solver.py

# Step 9 — Independent judge/verifier
python matr_final_verifier.py

# Step 10 — Prove the 5 false-negative cases (V20)
python matr_false_negative_closer.py
```

**Note:** Script 1 takes approximately 2 hours for 562 graphs.
Scripts 2–7 each take under 45 minutes. Script 10 closes open cases automatically.

---

## V23: Summary of Changes from V20

| Version | Key change |
|---|---|
| V20 | Script 10, Case 3b, 562 graphs verified, GAP=0 |
| V21 | **Patio Adjacency Lemma introduced** (Theorem 3.4) — main new result |
| V22 | Proof of Proposition 3.1 corrected; clear proved/open table |
| V23 | Honest title, Proposition framing, conditional Lemma 4.4, modern references |

**Open Problem 6.1:** Prove that branch sets can always be made simultaneously
connected and pairwise disjoint for any connected simple graph G with χ(G) = k.
This is equivalent to Hadwiger's conjecture for k ≥ 7.

---

## Visual Explanations

Open `visual/INDEX.html` in any browser for an interactive tour of the proof:
seven animated visualizations from the original sketch to the complete proof chain.

---

## Author

**Mizael Antonio Tovar Reyes**
Ciudad Juárez, Chihuahua, México — 2026

- Email: mizaelantoniotovarreyes@gmail.com
- GitHub: github.com/mizaelantoniotovarreyes

For commercial licensing inquiries, please contact the author directly.

---

## License

This work is released under a custom Research License.
Free for academic and personal use. Commercial use requires written permission.
See `LICENSE` for full terms.

---

## Preprint

This work is publicly available as a preprint on Zenodo (CERN):

- **DOI:** [10.5281/zenodo.19802214](https://doi.org/10.5281/zenodo.19802214)
- **URL:** https://zenodo.org/records/19802214

---

## Citation

If you use this work, please cite:

```
Tovar Reyes, M. A. (2026). A Patio Adjacency Lemma for Greedy Colorings,
with Computational Evidence Toward Branch-Set Connectivity (V23).
Zenodo. https://doi.org/10.5281/zenodo.19802214
GitHub: github.com/mizaelantoniotovarreyes/chromatic-hadwiger
```
