# Manual validation checklist (ngspice book)

Use this list when reviewing `docs/ngspice_book/` before declaring a snapshot complete. It mirrors the intent of [doument_prompt.md](../../../doument_prompt.md) validation guidance without running bulk generators.

## Structure

- [ ] Chapters `00_`–`24_` exist with `README.md` and expected section files per `_meta/section_manifest.tsv`.
- [ ] Root `INDEX.md` links resolve to chapter READMEs.
- [ ] BSIM6 omission documented in chapter 11 README / index notes (no `05_bsim6.md`).

## Per-section YAML

- [ ] Front matter includes `title`, `chapter`, `section`, `section_number`, `topic`, `mission_primary`, `related_files`, `related_chapters` where applicable.
- [ ] `canonical_chain_tags` (when present) are subsets of `rag_index.json` chain IDs.
- [ ] `related_files` entries exist in the ngspice tree (or are documented as external, e.g. PySpice-only sections).

## Citations and claims

- [ ] Substantive technical claims include `[Source: path#Lx]` or `<!-- source: path#Lx-Ly -->` citations.
- [ ] Paths match `_meta/path_registry.md` conventions for this repo (ngspice 26 layout).

## Cross-links

- [ ] Internal Markdown links resolve (no 404 paths relative to `docs/ngspice_book/`).
- [ ] Update `_meta/cross_reference_index.json` when adding major `related_chapters` edges; keep `broken_links` empty.

## Glossary and index

- [ ] Chapter 24 sections define terms with stable `{#anchors}`.
- [ ] `INDEX.md` word count remains in the 1500–3000 word band and reflects current omissions (BSIM6, XSPICE scope).

## `_meta` JSON hygiene

- [ ] `chapter_map.json` section counts match `section_manifest.tsv`.
- [ ] `source_file_attribution.json` lists only curated high-traffic sources (extend deliberately).
- [ ] `mission_coverage_matrix.json` notes mixed chapters (04, 11, 21, 23).

## Policy

- [ ] No book-body or `_meta` bulk generation scripts were added to the workflow (RAG index scripts may still maintain `rag_index.json` only).
