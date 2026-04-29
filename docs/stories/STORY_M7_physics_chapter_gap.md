# STORY M7 — Resolve missing chapter numbers 76–80 in `oracle_nav2.json` (Nav2 ledger)

**Branch:** `ngspice_rag`  
**Status:** 🔲 TODO  
**Severity:** 🟢 LOW — non-functional (book renders fine), cosmetic numbering gap

---

## Problem

`oracle_nav2.json` declares 115 chapters but uses chapter numbers 1–120 with **5 missing**: there are no entries for chapter numbers **76, 77, 78, 79, 80**.

The pipeline iterates `data.values()` and produces output filenames from the JSON keys, so the book will render `Chapter_075_*.md` then `Chapter_081_*.md` — a visible gap in the table of contents.

---

## Decision Required

Pick one of these three options. The story applies to whichever the maintainer chooses.

### Option A — Fill the gap with real chapters (recommended if Nav2 has enough untreated content)

Add 5 new entries covering Nav2 areas not yet in the oracle. Candidate topics (verify against Nav2 source tree before committing):

| Number | Suggested topic | Likely files |
|---|---|---|
| 076 | Behavior Tree XML Loading and Custom Node Plugins | `nav2_behavior_tree/src/behavior_tree_engine.cpp`, `nav2_behavior_tree/src/bt_action_node.cpp` |
| 077 | BT Navigator State Composition and Goal Lifecycle | `nav2_bt_navigator/src/bt_navigator.cpp`, `nav2_bt_navigator/src/navigators/navigate_to_pose.cpp` |
| 078 | Smoother Server Plugin Architecture | `nav2_smoother/src/nav2_smoother.cpp`, `nav2_constrained_smoother/src/constrained_smoother.cpp` |
| 079 | Velocity Smoother and Acceleration Limiter | `nav2_velocity_smoother/src/velocity_smoother.cpp` |
| 080 | Collision Monitor and Velocity Polygons | `nav2_collision_monitor/src/collision_monitor_node.cpp`, `nav2_collision_monitor/src/polygon.cpp` |

Each new entry must follow the existing schema:

```json
"Chapter_076_<slug>.md": {
  "chapter_title": "...",
  "files": ["<package>/src/<file>", ...],
  "research_prompt": "Perform a forensic extraction of ... CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### ...', '### ...', and '### ...'."
}
```

### Option B — Renumber chapters 81–120 down to 76–115

Rewrite all chapter keys from 81 onward to close the gap. This breaks any external reference to current chapter numbers (commit messages, issue threads, etc.) but produces a clean 1–115 sequence.

**Renumber mapping:**
- `Chapter_081_*.md` → `Chapter_076_*.md`
- `Chapter_082_*.md` → `Chapter_077_*.md`
- ...
- `Chapter_120_*.md` → `Chapter_115_*.md`

### Option C — Document the gap as intentional

If chapters 76–80 were intentionally removed (e.g. duplicate content, deferred topics), add a note in `crewai/README.md` and leave the JSON as-is. This is the lowest-effort path but should not be done without confirming the gap was deliberate.

---

## Implementation (assuming Option A — fill the gap)

### Step 1 — Audit the Nav2 source tree for true gaps

Before adding chapters, confirm the candidate topics are not already covered:

```bash
python3 -c "
import json
d = json.load(open('crewai/oracle_nav2.json'))
search_terms = ['behavior_tree', 'bt_navigator', 'smoother', 'velocity_smoother', 'collision_monitor']
for term in search_terms:
    hits = [k for k, v in d.items() if any(term in f for f in v.get('files', []))]
    print(f'{term}: {hits}')
"
```

If a candidate topic already has a chapter, pick a different topic.

### Step 2 — Add the 5 chapter entries

Insert into `oracle_nav2.json` at the correct alphabetical position (between `Chapter_075` and `Chapter_081`). Each new entry must:

- Use the existing schema (`chapter_title`, `files`, `research_prompt`).
- Include the `CRITICAL: ... '###' (H3) headers: ...` directive (matching the rest of the file — 100% of physics chapters already include this).
- Reference real, existing Nav2 source files.

### Step 3 — Verify integrity

```bash
python3 -c "
import json, re
d = json.load(open('crewai/oracle_nav2.json'))
nums = sorted([int(re.match(r'Chapter_(\d+)_', k).group(1)) for k in d.keys()])
assert len(nums) == len(set(nums)), 'Duplicate chapter numbers'
assert nums == list(range(1, len(nums)+1)), f'Non-sequential: missing {set(range(1, max(nums)+1)) - set(nums)}'
assert all('CRITICAL' in v.get('research_prompt','') for v in d.values()), 'Some chapters lack CRITICAL'
print(f'OK — {len(nums)} chapters, sequential 1-{max(nums)}, all have CRITICAL directive')
"
```

### Step 4 — (Optional) Validate file paths

If a Nav2 checkout is available, run the validator from Story M5:

```bash
python3 crewai/scripts/validate_oracle_paths.py crewai/oracle_nav2.json /path/to/navigation2
```

---

## Acceptance Criteria

- [ ] **One of:** (A) 5 new chapters added at numbers 76–80, OR (B) chapters 81–120 renumbered to 76–115, OR (C) gap documented in `crewai/README.md`.
- [ ] If Option A: all 5 new chapters reference real Nav2 source files and contain `CRITICAL: ... '###' (H3) headers: ...`.
- [ ] If Option A or B: integrity check (Step 3) reports `OK — 120 chapters, sequential 1-120` (A) or `OK — 115 chapters, sequential 1-115` (B).
- [ ] `oracle_nav2.json` remains valid JSON.
- [ ] Committed with message reflecting the chosen option, e.g. `fix(crewai): fill nav2 oracle gap with 5 missing chapters (76-80)`.
