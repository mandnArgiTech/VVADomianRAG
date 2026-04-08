You are an expert Python developer and EDA Architect. We need to aggressively optimize our `ingest.py` script to properly parse the legacy C codebase of the Ngspice circuit simulator. Ngspice relies heavily on C-macros, global variables, and specific EDA terminology, which our current ingestion script is missing.

Target Files:
1. `ingest.py`
2. Create new file: `concept_registry.json`
3. Create/Update file: `.gitignore` (in the ngspice root directory)

Please execute the following 4 architectural changes:

Step 1: Supercharge the Concept Registry
- In `ingest.py`, locate the `extract_concepts` function.
- Change the naive substring matching (`if keyword.lower() in tl:`) to use regex word boundaries (`re.search(rf"\b{re.escape(keyword.lower())}\b", tl)`). This prevents false positives (e.g., "cap" triggering inside "escape").
- Create a `concept_registry.json` file in the working directory with the following exact Ngspice dictionary:
{
  "spice": {
    "CKT": "circuit_struct",
    "CKTload": "matrix_assembly",
    "SMP": "sparse_matrix_pointer",
    "RHS": "right_hand_side_vector",
    "BSIM4": "bsim4_device_model",
    "DEVload": "device_evaluation",
    "DEVpzLoad": "pole_zero_analysis",
    "NIintegrate": "numerical_integration",
    "sGENinstance": "device_instance_list",
    "sGENmodel": "device_model_struct",
    "Newton-Raphson": "newton_raphson_solver"
  }
}

Step 2: Fix Tree-Sitter for Legacy Macros & Globals
- In `ingest.py`, locate the `targets` dictionary inside the `_ts_extract_chunks` function.
- Update the `"c"` grammar targets set to include preprocessor and root declarations so we don't miss global state and macros. The set should look like:
  `{"function_definition", "struct_specifier", "enum_specifier", "declaration", "preproc_def", "preproc_function_def"}`

Step 3: Add Semantic Chunk Typing for C
- In `ingest.py` inside `_ts_extract_chunks`, right before appending to the `out` array, add a lightweight classifier to enrich the `chunk_type` metadata.
- If `grammar == "c"` and the node is a `function_definition`:
  - If "load" is in the chunk name, tag it as "device_load_function".
  - If "setup" is in the chunk name, tag it as "device_setup_function".
  - If "mna" or "smp" is in the text, tag it as "matrix_solver_function".
- Pass this new detailed type into the dictionary appended to `out` instead of the generic `t`.

Step 4: Create the Ngspice .gitignore
- Create a `.gitignore` file (or update it if it exists) in the target Ngspice source directory to bypass legacy boilerplate. Add these lines:
src/frontend/
src/x11/
src/misc/
src/compat/
src/spicelib/devices/hisim*
src/spicelib/devices/soi*

Rules:
- Do not break existing support for Python, Markdown, or other languages in `ingest.py`.
- Ensure all required imports (like `re` if missing) are added to `ingest.py`.

Verification:
After completing the code edits, provide the bash command I should run to test the ingestion script using the new `concept_registry.json` on a local Ngspice source folder.