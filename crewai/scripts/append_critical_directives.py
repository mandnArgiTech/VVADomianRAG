#!/usr/bin/env python3
"""Append CRITICAL H3 directive to specific chapters in oracle_kinematica.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Baseline from STORY M6; refined to match each chapter's files[] in oracle_kinematica.json.
DIRECTIVES: dict[str, list[str]] = {
    "Chapter_131_Sailboat_WindVane_and_Tack_Gybe_Mechanics.md": [
        "### Apparent vs True Wind Vector Math (AP_WindVane.cpp)",
        "### Tack/Gybe State Machine (sailboat.cpp)",
        "### Mainsail Winch Servo Mapping (sailboat.cpp)",
    ],
    "Chapter_132_BalanceBots_and_Inverted_Pendulum_Kinematics.md": [
        "### Inverted Pendulum PID Loop (balance_bot.cpp)",
        "### EKF Pitch Fusion with Wheel Encoders (balance_bot.cpp)",
        "### UGV Mixer Overrides for Balance Recovery (AP_MotorsUGV.cpp)",
    ],
    "Chapter_133_Machine_Learning_Cruise_Throttle_Optimization.md": [
        "### Cruise Speed Delta Sampling (cruise_learn.cpp)",
        "### Real-Time Throttle Parameter Rewrite (cruise_learn.cpp)",
        "### Attitude PID Interaction with Learned Cruise Trim (AR_AttitudeControl.cpp)",
    ],
    "Chapter_134_Omnidirectional_Mecanum_Rover_Matrix_Mixing.md": [
        "### Mecanum 4-Wheel Mixing Matrix (AP_MotorsUGV.cpp)",
        "### Strafe Vector Decomposition (AP_MotorsUGV.cpp)",
        "### Yaw-Independent Translation Demands (AR_WPNav.cpp)",
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
        "### NavEKF3 Fusion of External Vision State (AP_NavEKF3_core.cpp)",
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
        "### IRLock I2C Pixel Read (IRLock.cpp)",
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
        "### Mission Logic via Applets (MissionSelector.lua)",
    ],
    "Chapter_143_MAVLink_FTP_and_Onboard_Filesystem_Management.md": [
        "### MAVLink FTP Burst-Read Protocol (GCS_FTP.cpp)",
        "### CRC and Resume Semantics (GCS_FTP.cpp)",
        "### SD Card Filesystem Abstraction (AP_Filesystem.cpp)",
    ],
    "Chapter_144_NMEA_Output_and_Marine_Chartplotter_Integration.md": [
        "### NMEA 0183 Sentence Encoding (AP_NMEA_Output.cpp)",
        "### EKF Global Position to GGA/RMC (AP_NMEA_Output.cpp)",
        "### Serial Port Routing for Marine Peripherals (AP_SerialManager.cpp)",
    ],
    "Chapter_145_Multi_Zone_Temperature_Calibration_and_IMU_Drift.md": [
        "### 3rd-Order Polynomial Bias Curve Math (AP_TempCalibration.cpp)",
        "### Per-Sensor Calibration Storage (AP_TempCalibration.cpp)",
        "### Runtime IMU Temp Correction Pipeline (AP_InertialSensor_tempcal.cpp)",
    ],
    "Chapter_146_Advanced_Failsafe_State_Machines_and_Geo_Sequences.md": [
        "### Programmable Geo-Sequence Parser (AP_AdvancedFailsafe.cpp)",
        "### Critical Subsystem Watchdog Hooks (AP_AdvancedFailsafe.cpp)",
        "### Rover-Specific Failsafe Dispatch (failsafe.cpp)",
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
        "### UAVCAN Transport and Companion Bus Integration (AP_UAVCAN.cpp)",
        "### MAVLink Message Definitions as Interop Schema (common.xml)",
        "### Decentralized Node Services and Routing (AP_UAVCAN.cpp)",
    ],
    "Chapter_150_The_ArduPilot_Compile_Time_ROMFS_and_Memory_Map.md": [
        "### ROMFS Embedded Header Generation (embed.py)",
        "### Compressed Asset Decoding (AP_ROMFS.cpp)",
        "### Memory-Mapped ROMFS Access Path (AP_ROMFS.cpp)",
    ],
}


def _format_directive(headers: list[str]) -> str:
    if len(headers) == 2:
        joined = f"'{headers[0]}' and '{headers[1]}'"
    elif len(headers) >= 3:
        joined = ", ".join(f"'{h}'" for h in headers[:-1]) + f", and '{headers[-1]}'"
    else:
        joined = f"'{headers[0]}'"
    return (
        " CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: "
        f"{joined}."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "oracle_json",
        nargs="?",
        type=Path,
        default=None,
        help="Path to oracle_kinematica.json (default: crewai/oracle_kinematica.json next to book_factory)",
    )
    args = ap.parse_args()
    crewai_dir = Path(__file__).resolve().parent.parent
    p = args.oracle_json.resolve() if args.oracle_json else crewai_dir / "oracle_kinematica.json"
    if not p.is_file():
        print(f"Not found: {p}", file=sys.stderr)
        return 2

    data = json.loads(p.read_text(encoding="utf-8"))
    changed = 0
    for ch_key, headers in DIRECTIVES.items():
        if ch_key not in data:
            print(f"  SKIP (missing): {ch_key}")
            continue
        prompt = data[ch_key].get("research_prompt", "")
        if "CRITICAL" in prompt:
            print(f"  SKIP (already has CRITICAL): {ch_key}")
            continue
        directive = _format_directive(headers)
        new_prompt = prompt.rstrip().rstrip(".") + "." + directive
        data[ch_key]["research_prompt"] = new_prompt
        changed += 1
        print(f"  UPDATED: {ch_key}")

    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{changed} chapters updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
