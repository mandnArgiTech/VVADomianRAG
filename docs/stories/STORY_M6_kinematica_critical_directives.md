# STORY M6 — Add `CRITICAL: H3 headers` directive to kinematica chapters 130–150

**Branch:** `ngspice_rag`  
**Status:** 🔲 TODO  
**Severity:** 🟡 MEDIUM — produces inconsistent chapter formatting (no functional break)

---

## Problem

`project_prompts_kinematica.json` task templates instruct the technical author to use specific `###` (H3) sub-section headers as **specified by the per-chapter `research_prompt`**. This works because chapters 1–130 each end their `research_prompt` with a directive like:

```
CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers:
'### The fast_loop() Microsecond Budget (Rover.cpp)',
'### Hardware Abstraction Boot Sequence (system.cpp)', and
'### Core Macro Constraints (defines.h)'.
```

**20 chapters (Chapter_131 through Chapter_150 inclusive) lack this directive entirely.** The author agent has no guidance on what H3 headers to use, leading to inconsistent / generic / missing sub-sections in the final book.

---

## Affected Chapters (20)

```
Chapter_131_Sailboat_WindVane_and_Tack_Gybe_Mechanics.md
Chapter_132_BalanceBots_and_Inverted_Pendulum_Kinematics.md
Chapter_133_Machine_Learning_Cruise_Throttle_Optimization.md
Chapter_134_Omnidirectional_Mecanum_Rover_Matrix_Mixing.md
Chapter_135_Torqeedo_Marine_Drives_and_IC_Engine_Generators.md
Chapter_136_Swarming_AP_Follow_and_Target_Offset_Math.md
Chapter_137_Visual_Odometry_VIO_and_External_Pose_Ingestion.md
Chapter_138_MultiWii_Serial_Protocol_MSP_and_Digital_OSD.md
Chapter_139_Crossfire_CRSF_and_High_Speed_RC_Telemetry.md
Chapter_140_Precision_Landing_IRLock_and_Companion_Targeting.md
Chapter_141_DroneCAN_Actuator_Arbitration_and_Node_Mapping.md
Chapter_142_Onboard_Lua_Applets_and_Peripheral_Sandboxing.md
Chapter_143_MAVLink_FTP_and_Onboard_Filesystem_Management.md
Chapter_144_NMEA_Output_and_Marine_Chartplotter_Integration.md
Chapter_145_Multi_Zone_Temperature_Calibration_and_IMU_Drift.md
Chapter_146_Advanced_Failsafe_State_Machines_and_Geo_Sequences.md
Chapter_147_Crash_Detection_Tip_Over_and_EKF_Variance_Watchdogs.md
Chapter_148_DataFlash_Log_Structure_and_High_Bandwidth_Ring_Buffers.md
Chapter_149_ROS_2_DDS_Integration_and_Micro_XRCE_Offloading.md
Chapter_150_The_ArduPilot_Compile_Time_ROMFS_and_Memory_Map.md
```

Note: `Chapter_130_ArduRover_Master_Control_Flow_and_Execution_Graph.md` is borderline — verify whether it has a CRITICAL block before this fix. If not, add it.

---

## Implementation

### Step 1 — Append a `CRITICAL` directive to each affected `research_prompt`

For each of the 20 chapters, **append** (do not replace) a directive matching the chapter's actual file list. The pattern from chapters 1–130 is:

```
CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### <topic 1> (<file1>)', '### <topic 2> (<file2>)', and '### <topic 3> (<file3>)'.
```

The headers must:

1. Start with `### `.
2. Describe a concrete sub-topic, not a generic one (e.g. `### Wind Triangle Vector Math (AP_WindVane.cpp)` not `### Implementation Details`).
3. Reference the **specific source file** in parentheses.
4. Use 2–4 headers per chapter (matching surrounding chapters' style).

### Step 2 — Suggested directives per chapter

Use these as a baseline — refine based on actual file contents:

```python
DIRECTIVES = {
    "Chapter_131_Sailboat_WindVane_and_Tack_Gybe_Mechanics.md": [
        "### Apparent vs True Wind Vector Math (AP_WindVane.cpp)",
        "### Tack/Gybe State Machine (sailboat.cpp)",
        "### Mainsail Winch Servo Mapping (sailboat.cpp)",
    ],
    "Chapter_132_BalanceBots_and_Inverted_Pendulum_Kinematics.md": [
        "### Inverted Pendulum PID Loop (balance_bot.cpp)",
        "### EKF Pitch Fusion with Wheel Encoders (balance_bot.cpp)",
        "### Throttle-to-Lean Override (balance_bot.cpp)",
    ],
    "Chapter_133_Machine_Learning_Cruise_Throttle_Optimization.md": [
        "### Cruise Speed Delta Sampling (cruise_learn.cpp)",
        "### Real-Time Throttle Parameter Rewrite (cruise_learn.cpp)",
        "### Convergence Criteria and Lockout (cruise_learn.cpp)",
    ],
    "Chapter_134_Omnidirectional_Mecanum_Rover_Matrix_Mixing.md": [
        "### Mecanum 4-Wheel Mixing Matrix (AP_MotorsUGV.cpp)",
        "### Strafe Vector Decomposition (AP_MotorsUGV.cpp)",
        "### Yaw-Independent Translation (AR_WPNav)",
    ],
    "Chapter_135_Torqeedo_Marine_Drives_and_IC_Engine_Generators.md": [
        "### Torqeedo CAN Handshake Protocol (AP_Torqeedo.cpp)",
        "### Generator Starter Sequencing (AP_Generator.cpp)",
        "### RPM Governor and Hybrid Arbitration (AP_Generator.cpp)",
    ],
    "Chapter_136_Swarming_AP_Follow_and_Target_Offset_Math.md": [
        "### MAVLink GLOBAL_POSITION_INT Ingestion (AP_Follow.cpp)",
        "### 3D Offset Vector Calculation (AP_Follow.cpp)",
        "### 50Hz Formation Update Loop (mode_follow.cpp)",
    ],
    "Chapter_137_Visual_Odometry_VIO_and_External_Pose_Ingestion.md": [
        "### 6-DOF Pose Unpacking (AP_VisualOdom.cpp)",
        "### Intel T265 Coordinate Frame Transform (AP_VisualOdom.cpp)",
        "### NavEKF3 Visual Position Fusion (AP_VisualOdom.cpp)",
    ],
    "Chapter_138_MultiWii_Serial_Protocol_MSP_and_Digital_OSD.md": [
        "### MSP Frame Format and Betaflight Spoofing (AP_MSP.cpp)",
        "### EKF Telemetry to MSP Translation (AP_MSP.cpp)",
        "### DisplayPort Canvas Rendering (AP_OSD.cpp)",
    ],
    "Chapter_139_Crossfire_CRSF_and_High_Speed_RC_Telemetry.md": [
        "### CRSF UART Frame Parser (AP_RCProtocol_CRSF.cpp)",
        "### 150Hz Stick Update Loop (AP_RCProtocol_CRSF.cpp)",
        "### Telemetry Downlink Interleaving (AP_RCTelemetry.cpp)",
    ],
    "Chapter_140_Precision_Landing_IRLock_and_Companion_Targeting.md": [
        "### IRLock I2C Pixel Read (AP_IRLock.cpp)",
        "### 2D Pixel to 3D Vector Math (AC_PrecLand.cpp)",
        "### Final Approach Velocity Damping (AC_PrecLand.cpp)",
    ],
    "Chapter_141_DroneCAN_Actuator_Arbitration_and_Node_Mapping.md": [
        "### CAN Bus Thread Priority Allocation (AP_CANManager.cpp)",
        "### Servo to Node ID Mapping (AP_UAVCAN.cpp)",
        "### Dynamic Hardware Discovery (AP_UAVCAN.cpp)",
    ],
    "Chapter_142_Onboard_Lua_Applets_and_Peripheral_Sandboxing.md": [
        "### Lua Script Loader and Sandbox (AP_Scripting.cpp)",
        "### CAN/I2C C++ Bindings (AP_Scripting.cpp)",
        "### Boxed Numeric Type Marshalling (AP_Scripting.cpp)",
    ],
    "Chapter_143_MAVLink_FTP_and_Onboard_Filesystem_Management.md": [
        "### MAVLink FTP Burst-Read Protocol (GCS_FTP.cpp)",
        "### CRC and Resume Semantics (GCS_FTP.cpp)",
        "### SD Card Filesystem Abstraction (AP_Filesystem.cpp)",
    ],
    "Chapter_144_NMEA_Output_and_Marine_Chartplotter_Integration.md": [
        "### NMEA 0183 Sentence Encoding (AP_NMEA_Output.cpp)",
        "### EKF Global Position to GGA/RMC (AP_NMEA_Output.cpp)",
        "### Serial Port Multiplexing (AP_NMEA_Output.cpp)",
    ],
    "Chapter_145_Multi_Zone_Temperature_Calibration_and_IMU_Drift.md": [
        "### 3rd-Order Polynomial Bias Curve Math (AP_TempCalibration.cpp)",
        "### Per-Sensor Calibration Storage (AP_TempCalibration.cpp)",
        "### Runtime Drift Correction Loop (AP_TempCalibration.cpp)",
    ],
    "Chapter_146_Advanced_Failsafe_State_Machines_and_Geo_Sequences.md": [
        "### Programmable Geo-Sequence Parser (AP_AdvancedFailsafe.cpp)",
        "### Critical Subsystem Watchdog Hooks (AP_AdvancedFailsafe.cpp)",
        "### Termination Action Dispatcher (AP_AdvancedFailsafe.cpp)",
    ],
    "Chapter_147_Crash_Detection_Tip_Over_and_EKF_Variance_Watchdogs.md": [
        "### Inversion Detection Math (crash_check.cpp)",
        "### EKF Compass Variance Monitor (ekf_check.cpp)",
        "### Manual-Fallback Trigger Logic (crash_check.cpp)",
    ],
    "Chapter_148_DataFlash_Log_Structure_and_High_Bandwidth_Ring_Buffers.md": [
        "### Non-Blocking DMA Ring Buffer (AP_Logger.cpp)",
        "### LogStructure Packing and Versioning (LogStructure.h)",
        "### Hard-Fault Recovery Guarantees (AP_Logger.cpp)",
    ],
    "Chapter_149_ROS_2_DDS_Integration_and_Micro_XRCE_Offloading.md": [
        "### Micro XRCE-DDS Client Setup (AP_DDS_Client.cpp)",
        "### ArduPilot State to ROS 2 Topic Translation (AP_DDS_Client.cpp)",
        "### Ethernet Transport and QoS Profiles (AP_DDS_Client.cpp)",
    ],
    "Chapter_150_The_ArduPilot_Compile_Time_ROMFS_and_Memory_Map.md": [
        "### ROMFS Build-Time C-Array Generation (romfs.py)",
        "### Compressed Asset Decoding (AP_ROMFS.cpp)",
        "### Memory Map and Hex Layout (AP_ROMFS.cpp)",
    ],
}
```

### Step 3 — Migration script

Create `crewai/scripts/append_critical_directives.py`:

```python
"""Append CRITICAL H3 directive to specific chapters in oracle_kinematica.json."""
import json
from pathlib import Path

DIRECTIVES = { ... }  # paste from Step 2

def main():
    p = Path("crewai/oracle_kinematica.json")
    data = json.loads(p.read_text())
    changed = 0
    for ch_key, headers in DIRECTIVES.items():
        if ch_key not in data:
            print(f"  SKIP (missing): {ch_key}")
            continue
        prompt = data[ch_key].get("research_prompt", "")
        if "CRITICAL" in prompt:
            print(f"  SKIP (already has CRITICAL): {ch_key}")
            continue
        # Format the directive matching the chapters 1-130 pattern
        if len(headers) == 2:
            joined = f"'{headers[0]}' and '{headers[1]}'"
        elif len(headers) >= 3:
            joined = ", ".join(f"'{h}'" for h in headers[:-1]) + f", and '{headers[-1]}'"
        else:
            joined = f"'{headers[0]}'"
        directive = f" CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: {joined}."
        # Append (preserve existing trailing punctuation)
        new_prompt = prompt.rstrip().rstrip(".") + "." + directive
        data[ch_key]["research_prompt"] = new_prompt
        changed += 1
        print(f"  UPDATED: {ch_key}")

    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n{changed} chapters updated.")

if __name__ == "__main__":
    main()
```

### Step 4 — Verify with the audit query

After running the migration, this command must report `0`:

```bash
python3 -c "
import json
d = json.load(open('crewai/oracle_kinematica.json'))
missing = [k for k, v in d.items() if 'CRITICAL' not in v.get('research_prompt','')]
print(f'Chapters still missing CRITICAL: {len(missing)}')
for k in missing: print(f'  {k}')
"
```

---

## Acceptance Criteria

- [ ] All 20 chapters listed above contain `CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: ...` in their `research_prompt`.
- [ ] H3 headers reference specific source files from the chapter's `files` list (no generic placeholders).
- [ ] The audit query above reports `Chapters still missing CRITICAL: 0`.
- [ ] `oracle_kinematica.json` remains valid JSON (`python3 -c "import json; json.load(open('crewai/oracle_kinematica.json'))"`).
- [ ] `crewai/scripts/append_critical_directives.py` is committed alongside the data change for reproducibility.
- [ ] Committed with message `fix(crewai): add CRITICAL H3 directive to 20 kinematica chapters`.
