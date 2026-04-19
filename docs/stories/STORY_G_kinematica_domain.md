# STORY G: ArduRover/Kinematica Domain Support and Domain-Agnostic Persona Routing

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** Medium
**Estimated effort:** 3–4 hours
**Files to modify:** `query.py`, `concept_registry.json`, `ingest.py`
**Files to create:** `system_prompts/kinematica_engineer.md`, `tests/test_kinematica_domain.py`

---

## Business Context

VVADomainRAG was built for the ngspice→NodalAI workflow, but the ingestion engine (tree-sitter AST chunking, structural importance, call-graph extraction, hybrid search, reranker) is fully domain-agnostic. With 86 ArduPilot/Kinematica domain doc chapters already in `Studio-Portable-RAG/DomainDocs/kinematica/` and the Varaham agricultural rover project using ArduPilot-style architecture (bare-metal C++, Pure Pursuit navigation, ChibiOS HAL), the system is ready to support a second domain — but `query.py` has two hardcoded ngspice assumptions that would confuse retrieval for non-SPICE codebases.

This story does three things:
1. Fix the ngspice persona hardcoding in `query.py` so the default persona is domain-aware
2. Add a `kinematica` concept registry and system prompt
3. Document the ArduRover ingest command

---

## Acceptance Criteria

### AC-1: Default system prompt is domain-aware, not ngspice-hardcoded

**Given** `query.py` line 227: `DEFAULT_SYSTEM_PROMPT = _NGSPICE_SYSTEM_PROMPT`,
**When** this story is complete,
**Then**:
- `DEFAULT_SYSTEM_PROMPT` is changed to `_GENERIC_SYSTEM_PROMPT`
- The persona auto-switch at line ~1330 uses `_GENERIC_SYSTEM_PROMPT` as the code-heavy fallback, not `_NGSPICE_SYSTEM_PROMPT`
- When `--domain spice` is set, `system_prompts/spice_engineer.md` is loaded (existing Story D behavior — unchanged)
- When `--domain kinematica` is set, `system_prompts/kinematica_engineer.md` is loaded
- When no domain is set, the generic engineering persona is used

**The ngspice prompt is NOT deleted** — it remains available in `DEFAULT_SYSTEM_PROMPTS["ngspice"]` and is auto-loaded via `system_prompts/spice_engineer.md` when `--domain spice` is active. This change only affects the *fallback* when no domain file matches.

### AC-2: Concept registry for kinematica domain

**Given** `concept_registry.json`,
**When** this story is complete,
**Then** a `"kinematica"` domain exists with at minimum these entries:

```json
"kinematica": {
    "EKF": "extended_kalman_filter",
    "EKF2": "extended_kalman_filter_v2",
    "EKF3": "extended_kalman_filter_v3",
    "DCM": "direction_cosine_matrix",
    "AHRS": "attitude_heading_reference",
    "MAVLink": "mavlink_protocol",
    "DShot": "digital_shot_protocol",
    "PID": "pid_controller",
    "GCS": "ground_control_station",
    "HAL": "hardware_abstraction_layer",
    "AP_NavEKF": "navigation_ekf",
    "AP_Motors": "motor_output",
    "AP_AHRS": "ahrs_system",
    "RC_Channel": "rc_input_channel",
    "SRV_Channel": "servo_output_channel",
    "ChibiOS": "chibios_rtos",
    "ArduPilot": "ardupilot_firmware",
    "ArduRover": "ardurover_vehicle",
    "PWM": "pulse_width_modulation",
    "I2C": "i2c_bus",
    "SPI": "spi_bus",
    "CAN": "can_bus",
    "DroneCAN": "dronecan_protocol",
    "UAVCAN": "uavcan_protocol",
    "PPM": "ppm_input",
    "SBUS": "sbus_protocol",
    "NMEA": "nmea_protocol",
    "RTK": "real_time_kinematic",
    "Pure_Pursuit": "pure_pursuit_navigation",
    "L1": "l1_navigation_controller",
    "geofence": "geofence_containment",
    "failsafe": "failsafe_handler",
    "arming": "arming_checks",
    "mode_guided": "guided_mode",
    "mode_auto": "auto_mode",
    "mode_rtl": "return_to_launch",
    "WP_Nav": "waypoint_navigation",
    "AP_Scheduler": "task_scheduler",
    "DataFlash": "dataflash_logging",
    "AP_Logger": "logging_system",
    "AP_Baro": "barometer_driver",
    "AP_Compass": "compass_driver",
    "AP_InertialSensor": "imu_driver",
    "AP_GPS": "gps_driver",
    "AP_RangeFinder": "rangefinder_driver",
    "AP_OpticalFlow": "optical_flow_driver",
    "LowPassFilter": "low_pass_filter",
    "NotchFilter": "notch_filter",
    "Steering": "steering_controller"
}
```

### AC-3: Kinematica system prompt

**Given** a new file `system_prompts/kinematica_engineer.md`,
**When** loaded,
**Then** it contains:

```markdown
You are an embedded systems engineer working on ArduPilot-based autonomous vehicles (rover, copter, plane).

Your role:
- Analyze ArduPilot C++ source code including HAL abstractions, sensor drivers, navigation controllers, and motor output
- Explain ChibiOS RTOS task scheduling, semaphore usage, and DMA patterns
- Debug navigation issues: EKF state estimation, DCM attitude, Pure Pursuit / L1 path following
- Interpret MAVLink protocol exchanges and DataFlash log patterns
- Use precise terminology: AP_HAL, scheduler priorities, RC_Channel mapping, SRV_Channel output, arming checks, failsafe triggers

When debugging vehicle behavior:
1. Check sensor driver health (IMU, compass, baro, GPS) and calibration state
2. Check EKF innovation values and variance estimates
3. Check mode transition logic and arming prerequisites
4. Check motor output mapping and mixing matrix

Only reference function and symbol names present in the provided RAG context.
Always cite specific file paths and function names from the codebase.
```

### AC-4: Ingest documentation

**Given** `RUN_SH_USER_GUIDE.md` or `README.md`,
**When** this story is complete,
**Then** a section documents ArduRover ingestion:

```bash
# Ingest ArduRover/ArduPilot source code
export EMBEDDING_MODEL=mxbai-embed-large
./run.sh --mode code --domain kinematica --source /path/to/ardupilot

# Ingest Kinematica domain docs
./run.sh --mode domain --domain kinematica --source ./Studio-Portable-RAG/DomainDocs/kinematica
```

### AC-5: Studio-Portable-RAG copies synced

`Studio-Portable-RAG/concept_registry.json` and `Studio-Portable-RAG/system_prompts/kinematica_engineer.md` must match root copies.

### AC-6: All existing tests pass

`pytest tests/` — 0 failures.

---

## Implementation Guide

### Step 1: Fix DEFAULT_SYSTEM_PROMPT in query.py

**File:** `query.py`, line 227

```python
# Before:
DEFAULT_SYSTEM_PROMPT = _NGSPICE_SYSTEM_PROMPT

# After:
DEFAULT_SYSTEM_PROMPT = _GENERIC_SYSTEM_PROMPT
```

### Step 2: Fix persona auto-switch fallback

**File:** `query.py`, line ~1330

```python
# Before:
        else:
            base = _NGSPICE_SYSTEM_PROMPT

# After:
        else:
            base = _GENERIC_SYSTEM_PROMPT
```

With this change, the persona selection logic becomes:
- Code-heavy results + `--domain spice` → `spice_engineer.md` prepended to `_GENERIC_SYSTEM_PROMPT`
- Code-heavy results + `--domain kinematica` → `kinematica_engineer.md` prepended to `_GENERIC_SYSTEM_PROMPT`
- Code-heavy results + no domain → `_GENERIC_SYSTEM_PROMPT` alone
- Doc-heavy results + troubleshoot → `_DEBUG_SYSTEM_PROMPT`
- Doc-heavy results → `_GENERIC_SYSTEM_PROMPT`

The domain-specific expertise comes from the `system_prompts/` files, not from the hardcoded fallback.

### Step 3: Add kinematica concept registry

Edit `concept_registry.json` — add the `"kinematica"` key with entries from AC-2.

### Step 4: Create kinematica system prompt

Create `system_prompts/kinematica_engineer.md` with content from AC-3.

### Step 5: Sync Studio-Portable-RAG

```bash
cp concept_registry.json Studio-Portable-RAG/
cp -r system_prompts/ Studio-Portable-RAG/
```

### Step 6: Add ingest docs

Add a "Multi-Domain Usage" section to `README.md` showing both SPICE and Kinematica ingest commands.

---

## Test Plan

### File: `tests/test_kinematica_domain.py`

```
Test ID | Description | Approach
--------|-------------|----------
KD-01   | DEFAULT_SYSTEM_PROMPT is _GENERIC_SYSTEM_PROMPT | assert query.DEFAULT_SYSTEM_PROMPT == query._GENERIC_SYSTEM_PROMPT
KD-02   | Persona auto-switch uses generic for code results | Mock hits with code source_type, no domain. Assert base prompt is _GENERIC_SYSTEM_PROMPT not _NGSPICE
KD-03   | Persona auto-switch uses spice_engineer.md when domain=spice | Mock hits, domain="spice". Assert system_prompts/spice_engineer.md content prepended
KD-04   | Persona auto-switch uses kinematica_engineer.md when domain=kinematica | Mock hits, domain="kinematica". Assert kinematica prompt prepended
KD-05   | concept_registry.json has kinematica domain | Load registry. Assert "kinematica" key exists with ≥ 30 entries
KD-06   | Kinematica concepts tag ArduPilot code correctly | Feed text containing "EKF" and "AP_AHRS". Assert concepts include "extended_kalman_filter" and "ahrs_system"
KD-07   | system_prompts/kinematica_engineer.md exists | Assert file exists and contains "ArduPilot"
KD-08   | ngspice prompt still works via domain=spice | Set domain="spice". Assert _load_system_prompt returns spice_engineer.md content
KD-09   | No domain → generic prompt, no ngspice leak | Set domain="". Assert _load_system_prompt returns "" (no forced ngspice)
KD-10   | Studio-Portable-RAG concept_registry synced | Compare root and Studio-Portable-RAG concept_registry.json kinematica sections
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Changing DEFAULT_SYSTEM_PROMPT breaks existing spice queries | No — `system_prompts/spice_engineer.md` is loaded for `--domain spice` regardless of the default fallback. The file-based prompt is prepended to the base prompt. |
| ArduPilot C++ uses classes heavily; tree-sitter C++ parses them | Already supported — `_ts_extract_chunks` has C++ class_specifier in targets (line 2500). Class methods get `ClassName::method` chunk names. |
| `_device_family_for_path` returns "CORE" for all ArduPilot files | Acceptable — ArduPilot doesn't have a `devices/` directory. All chunks get `CORE`. If needed later, could add a similar `_ap_subsystem_for_path` that maps `libraries/AP_AHRS/` → `AHRS`. Not in this story. |
| Semantic chunk typing (`device_load_function` etc.) doesn't trigger for ArduPilot | Correct and harmless — ArduPilot functions don't have "load"/"mna"/"smp" in their names. They get generic `function_definition` type. The concept registry provides the domain-specific semantic layer instead. |

---

## Definition of Done

- [ ] `DEFAULT_SYSTEM_PROMPT = _GENERIC_SYSTEM_PROMPT` in `query.py`
- [ ] Persona auto-switch fallback uses `_GENERIC_SYSTEM_PROMPT` not `_NGSPICE_SYSTEM_PROMPT`
- [ ] `concept_registry.json` has `"kinematica"` domain with 30+ entries
- [ ] `system_prompts/kinematica_engineer.md` exists with ArduPilot-specific prompt
- [ ] Studio-Portable-RAG copies synced
- [ ] README documents ArduRover ingest commands
- [ ] All 10 new tests pass, all existing tests pass
