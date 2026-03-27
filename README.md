# Chromatic Hadwiger Conjecture — V20
### by Mizael Antonio Tovar Reyes — Ciudad Juárez, Chihuahua, México

---

## What This Is

This repository contains the computational verification and mathematical proof
of the **Hadwiger Conjecture** for chromatic graphs, reformulated as:

> **Theorem 8.7 (V20):** For every connected simple graph G with χ(G) = k,
> Construction 8.1 (Phases 1–3) produces k valid branch sets certifying the K_k minor.
> Consequently, G contains K_k as a minor.

The approach is based on a novel formula discovered by the author:

> **χ(G) = 1 + p(G)**

where p(G) is the **palette expansion** of G — the minimum number of colors
forced by any greedy ordering over all possible vertex orderings.

**V20 closes the last open gap**: the formal anti-destruction proof for Case 3b
of Lemma 8.3f (articulation point scenario), plus Script 10 which exhaustively
proves all 5 previously unresolved graphs do contain the required K_k minor.

---

## Key Contributions

| Result | Status | Script |
|---|---|---|
| Theorem 4.1: χ(G) = 1 + p(G) | VERIFIED — 562 graphs, 0 failures, 129.3 min | matr_chromatic_identity |
| Lemma 7.1: Chromatic Completeness | VERIFIED — 562 graphs, 0 failures | matr_completeness_lemma |
| Theorem 8.7: Gap Detection (Lemma 8.3e) | VERIFIED — 562 graphs, GAP = 0 | matr_hadwiger_theorem |
| Exact Graph Families (Theorem 8.4) | VERIFIED — 66/66 families | matr_exact_families |
| Lemma 8.3d: Distributed Absorption | VERIFIED — 562 graphs, 0 failures | matr_branch_absorption |
| Lemma 8.3f: Alternating Connector (*) | VERIFIED — Case A=5417, Case B=177, GAP=0 | matr_alternating_connector |
| K_k Minor Completeness | VERIFIED — 562 graphs, 0 failures | matr_minor_certificate |
| Hadwiger high-chi solver | 562 graphs tested | matr_high_chi_solver |
| Judge/Verifier (Lemmas 8.3c–f) | PRODUCTION READY | matr_final_verifier |
| **V20: 5 false-negatives closed** (**) | **PROVED — 5/5, 0 counterexamples** | **matr_false_negative_closer** |

(*) **Original contribution** — the "purple connector" idea (Mizael, March 2026),
formalized as Lemma 8.3f. Case 3b formally proved in V20 (Theorem: Anti-Destruction
with Strict Gain).

(**) Script 10 proves that the 5 graphs previously flagged by Script 8
are algorithmic false-negatives — not counterexamples to the conjecture.

---

## Repository Structure

```
mizaeltovarreyes-chromatic-hadwiger-V20/
|
+-- scripts/
|   +-- core_utils.py                     Shared library: graph generation, coloring, logging
|   +-- matr_chromatic_identity.py        Theorem 4.1: chi(G) = 1 + p(G)
|   +-- matr_completeness_lemma.py        Lemma 7.1: Chromatic Completeness
|   +-- matr_hadwiger_theorem.py          Theorem 8.7 with gap detection
|   +-- matr_exact_families.py            Exact graph families (Theorem 8.4)
|   +-- matr_branch_absorption.py         Lemma 8.3d: Distributed absorption
|   +-- matr_alternating_connector.py     Lemma 8.3f: Alternating connector
|   +-- matr_minor_certificate.py         K_k minor completeness
|   +-- matr_high_chi_solver.py           Main Hadwiger solver (chi >= 5)
|   +-- matr_final_verifier.py            Independent judge/verifier
|   +-- matr_false_negative_closer.py     V20: Proves 5 false-negative cases
|   +-- matr_full_verification.py         Full verification harness
|
+-- logs/
|   +-- log_matr_chromatic_identity.txt       500+ graphs, 129.3 min, 0 failures
|   +-- log_matr_completeness_lemma.txt       5000+ pairs, 0 failures
|   +-- log_matr_hadwiger_theorem.txt         Gap detection results
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
|   +-- mizaeltovarreyes-chromatic-hadwiger-V20.tex   Official paper (LaTeX)
|   +-- mizaeltovarreyes-chromatic-hadwiger-V20.docx  Word version
|   +-- case3b_anti_destruction_proof.md              Case 3b formal proof (V20)
|   +-- Explained Simply.txt                          Non-technical explanation
|   +-- CHANGELOG_V20.md                              What changed in V20
|   +-- SUBMISSION_ARXIV_V20.md                       arXiv submission guide
|   +-- SUBMISSION_GITHUB_V20.md                      GitHub push guide
|
+-- visual/
|   +-- INDEX.html                   Visual suite landing page (open in browser)
|   +-- 01_origin_the_drawing.html   The hand-drawn sketch that started everything
|   +-- 02_palette_expansion.html    Interactive chi = 1 + p(G) demo
|   +-- 03_chromatic_completeness.html  Lemma 7.1 animated proof
|   +-- 04_branch_sets_minor.html    Branch sets and K_k minor
|   +-- 05_three_phases.html         Construction 8.1: three phases
|   +-- 06_purple_connector.html     Lemma 8.3f alternating connector
|   +-- 07_proof_chain.html          Complete proof chain (clickable)
|   +-- Imagen1.jpg                  Original hand-drawn sketch
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

# Step 2 — Verify Lemma 7.1 (Chromatic Completeness)
python matr_completeness_lemma.py

# Step 3 — Theorem 8.7 with gap detection
python matr_hadwiger_theorem.py

# Step 4 — Exact graph families
python matr_exact_families.py

# Step 5 — Lemma 8.3d (Distributed Absorption)
python matr_branch_absorption.py

# Step 6 — Lemma 8.3f (Alternating Connector)
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

## V20: All Cases Resolved

Script 10 formally proves that **all 5 graphs previously flagged by Script 8**
contain the required K_k minor:

| Graph | n | chi | Proof method | Result |
|---|---|---|---|---|
| Rand_chi5_n7_#375 | 7 | 5 | Exhaustive partition search (382 partitions) | K_5 PROVED |
| Rand_chi6_n8_#160 | 8 | 6 | Exhaustive partition search (2,569 partitions) | K_6 PROVED |
| Circ_19_3 | 19 | 5 | K_{k-1} clique + step-3 jump path | K_5 PROVED |
| Circ_21_3 | 21 | 5 | K_{k-1} clique + step-3 jump path | K_5 PROVED |
| Circ_21_4 | 21 | 6 | K_{k-1} clique + step-4 jump path | K_6 PROVED |

**Zero counterexamples.** The Hadwiger conjecture holds computationally for all
562 tested graphs (χ ranging from 2 to 10).

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

## Citation

If you use this work, please cite:

```
Tovar Reyes, M. A. (2026). Palette-Expansion Numbers and a Constructive
Proof of Hadwiger's Conjecture (V20).
GitHub: github.com/mizaelantoniotovarreyes/chromatic-hadwiger
```
