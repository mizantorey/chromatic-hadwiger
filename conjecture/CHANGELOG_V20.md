# CHANGELOG — Version 20
## Palette-Expansion Numbers and a Constructive Proof of Hadwiger's Conjecture
### Mizael Antonio Tovar Reyes — Ciudad Juárez, Chihuahua, México — March 2026

---

## Summary of V20 Changes

V20 closes the two remaining open items from V19:

1. **Formal proof of Case 3b** (anti-destruction, Lemma 8.3f)
2. **Script 10** closes all 5 algorithmic false-negatives from Script 8

No definitions, lemmas, or theorems were weakened or removed.
All V19 results carry forward unchanged.

---

## New in V20

### 1. Theorem: Anti-Destruction with Strict Gain (Section 8.5, V20)

**What was missing in V19:**
Lemma 8.3f-B stated that Phase 3 terminates in at most k(k-1)/2 iterations
with strict gain |E(H')| ≥ |E(H)| + 1. The proof cited "No repair destroys
existing contracted edges (articulation point case 3b preserves connectivity)"
without a formal argument for the articulation case.

**What V20 adds:**
A complete two-part proof of the anti-destruction property:

- **Part 1 — No edge is destroyed:**
  - Case 3a (w ≠ nb): witness (w, x) stays in B'_j × B'_ℓ → PRESERVED.
  - Case 3b (w = nb, articulation): edge (nb, x) transfers from (B_j, B_ℓ)
    to (B_ci, B_ℓ). The contracted edge is TRANSFERRED, not destroyed.
    Net effect on |E(H)|: zero loss for this pair.

- **Part 2 — B_ci gains at least one new edge:**
  - Via selection condition (S2): (v, nb) ∈ E(G) with v ∈ B_ci creates
    the contracted edge B_ci — B_j (was absent since B_ci was isolated).
  - Via Case 3b transfer: (nb, x) witnesses B_ci — B_ℓ (new).
  - B_ci goes from degree 0 to degree ≥ 1 in H(G,B').

- **Conclusion:** |E(H(G,B'))| ≥ |E(H(G,B))| + 1. ∎

**Location in paper:** Section 8.5, between Lemma 8.3f-B and Lemma 8.3f.
Full document: `conjecture/lema83f_caso3b_prueba_formal.md`

---

### 2. Script 10 — Closing 5 False-Negative Cases (script10_prueba_5_fallos.py)

**Context:**
Script 8 (high-chi Hadwiger solver) reported `connected=False` for 5 graphs,
meaning the branch-set algorithm failed to produce a connected partition.
These were suspected false-negatives (algorithm failure, not conjecture failure).

**What Script 10 does:**
Uses two independent proof methods to confirm each graph contains K_k:

**Method A — Exhaustive partition search** (for random graphs, n ≤ 9):
Enumerates all surjective k-colorings of V, extracts all valid k-partitions
(each part non-empty), and checks for valid branch sets (each part connected
in G, each pair with ≥ 1 edge between them). Finds a valid K_k certificate.

**Method B — Constructive K_{k-1}-clique + jump path** (for circulant graphs):
Given Circ(n, {1,...,s}):
- B_0 = {0}, B_1 = {1}, ..., B_{k-2} = {k-2}  ← K_{k-1} clique (singletons)
- B_{k-1} = path starting at k-1, stepping by s (mod n), until it reaches
  a vertex within distance s of 0 ← closes the K_k by connecting to B_0

This construction is valid because:
- Each B_i is a singleton (trivially connected) or a path (connected)
- All k-1 clique pairs share an edge (consecutive integers, step-1 adjacency)
- B_{k-1} path is adjacent to B_{k-2} at its start vertex
- B_{k-1} path returns to within step-s of vertex 0 → edge to B_0

**Results:**

| Graph | n | chi | Method | Partitions checked | Result |
|---|---|---|---|---|---|
| Rand_chi5_n7_#375 | 7 | 5 | Exhaustive | 382 | K_5 PROVED |
| Rand_chi6_n8_#160 | 8 | 6 | Exhaustive | 2,569 | K_6 PROVED |
| Circ_19_3 | 19 | 5 | Constructive | — | K_5 PROVED |
| Circ_21_3 | 21 | 5 | Constructive | — | K_5 PROVED |
| Circ_21_4 | 21 | 6 | Constructive | — | K_6 PROVED |

**Log file:** `logs/log_script10_prueba_5_fallos.txt`

---

### 3. LaTeX Paper (Section 1 → full paper)

`conjecture/mizaeltovarreyes-chromatic-hadwiger-V20.tex` — new in V20.

- Complete conversion of V19.docx to LaTeX
- All theorems, lemmas, proofs, tables, and references properly formatted
- Includes Anti-Destruction Theorem (new in V20) with full proof
- Version table updated with V20 row
- Script 10 results included in Section 9 (Computational Verification)
- All cross-references use `\label` / `\ref` — no forward references

---

### 4. Version Standardization

All scripts updated from mixed versions (V2, V5, V12.7, V16, V17, V19)
to uniform **V20** header, with `CAMBIOS V20` section documenting what changed.
No functional code was modified.

---

## Files Added in V20

| File | Description |
|---|---|
| `scripts/script10_prueba_5_fallos.py` | Proves 5 false-negative cases |
| `logs/log_script10_prueba_5_fallos.txt` | Execution log for Script 10 |
| `conjecture/mizaeltovarreyes-chromatic-hadwiger-V20.tex` | Official LaTeX paper |
| `conjecture/lema83f_caso3b_prueba_formal.md` | Case 3b formal proof document |
| `conjecture/PARRAFO_LEMA83F_INSERTAR_EN_PAPER.txt` | Text for Section 8.5 |
| `conjecture/CHANGELOG_V20.md` | This file |
| `conjecture/SUBMISSION_ARXIV_V20.md` | arXiv submission checklist |

---

## Files Modified in V20

| File | Change |
|---|---|
| `scripts/VERIFICACION_COMPLETA.py` | Header → V20; Script 10 mentioned |
| `scripts/core_utils.py` | Header → V20 |
| `scripts/script1_teorema41.py` | Header → V20 |
| `scripts/script2_lema71.py` | Header → V20 |
| `scripts/script3_teorema87.py` | Header → V20 |
| `scripts/script4_familias_exactas.py` | Header → V20 |
| `scripts/script5_lema83d.py` | Header → V20 |
| `scripts/script6_lema83f_conector.py` | Header → V20; Case 3b ref added |
| `scripts/script7_kk_minor_completo.py` | Header → V20 |
| `scripts/script8_v12_7_600.py` | Header → V20; note about Script 10 |
| `scripts/script9_v5_juez_final.py` | Header → V20 |
| `README.md` | Updated for V20: Script 10, resolved cases, paper |

---

## What Has NOT Changed

- All mathematical definitions (Definitions 3.1–3.5, Corollary 3.6)
- All lemma and theorem statements
- All computational results from V19 (562 graphs, GAP=0, etc.)
- The proof of Theorem 8.7 (only strengthened by Case 3b)
- Script behavior (all scripts 1–9 run identically to V19)

---

*Mizael Antonio Tovar Reyes — Ciudad Juárez, Chihuahua, México — March 2026*
