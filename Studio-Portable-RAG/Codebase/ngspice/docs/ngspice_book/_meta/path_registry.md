# Path registry (prompt examples vs ngspice v26 tree)

Use the **Use instead** column in citations and `related_files`. The book is authored against this checkout, not legacy SPICE3 path names from older docs.

| Topic | Wrong / legacy example | Use in this tree |
|-------|------------------------|------------------|
| Newton–Raphson driver | `src/spicelib/analysis/niiter.c` | `src/maths/ni/niiter.c` |
| Convergence test | `src/spicelib/analysis/niconv.c` | `src/maths/ni/niconv.c` (`NIconvTest`) |
| Circuit init | `src/spicelib/analysis/cktinit.c` | `src/spicelib/devices/cktinit.c` |
| Integration / predict / cofactors | (often “under analysis”) | `src/maths/ni/niinteg.c`, `nicomcof.c`, `nipred.c` |
| Transient accept | — | `src/spicelib/devices/cktaccept.c` |
| Dot commands | `src/frontend/inpdot.c` | `src/frontend/dotcards.c` (+ `inp2*.c` as needed) |
| Model table in parser | `inpdomod.c` only in frontend | `src/spicelib/parser/inpdomod.c` |
| Transfer function | `tfan.c` | `src/spicelib/analysis/tfanal.c` |
| Distortion | `disto.c` | `src/spicelib/analysis/distoan.c` |
| Sensitivity | `senan.c` / `sense2.c` only | `src/spicelib/analysis/cktsens.c`, `senssetp.c`, `sensaskq.c` — confirm task wiring in `analysis.c` |
| Measure | `measure/` subdirectory only | `src/frontend/measure.c`, `com_measure2.c` |
| Raw output | `raw.c` | `src/frontend/rawfile.c` |

## Honest omissions in this book tree

- **BSIM6:** There is no `src/spicelib/devices/bsim6/` — section `11_mosfet_models/05_bsim6.md` is **not** present. Chapter 11 README and `INDEX.md` state this.
- **Chapter 13 (XSPICE):** Included because `src/xspice/` exists in this repository.

## Inventory

- Section list: [`section_manifest.tsv`](section_manifest.tsv) (191 section files + chapter READMEs + `INDEX.md`).
