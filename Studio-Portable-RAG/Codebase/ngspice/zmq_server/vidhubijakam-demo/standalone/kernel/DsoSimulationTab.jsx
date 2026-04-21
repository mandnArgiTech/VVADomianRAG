import DsoScope from "./DsoScope.jsx";
import { fe } from "./formatValue.js";

/** Waveform-only simulation view (AC / TRAN / DC sweep) for bottom tool window. */
export default function DsoSimulationTab(props) {
  var r = props.r;
  if (!r) {
    return (
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#888",
          fontFamily: "'Segoe UI',sans-serif",
          fontSize: 13,
          background: "#1E1E1E",
        }}
      >
        Run a simulation to see waveforms (AC / TRAN / DC sweep).
      </div>
    );
  }

  var ac = r.ac_sweep;
  var tr = r.transient;
  var sw = r.dc_sweep;
  var cl = ["#0060C0", "#D04020", "#008040", "#8040A0", "#C06000", "#006080"];

  if (!ac && !tr && !sw) {
    return (
      <div
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#888",
          fontFamily: "'Segoe UI',sans-serif",
          fontSize: 13,
          background: "#1E1E1E",
        }}
      >
        No waveform data. This response has no AC sweep, transient time series, or DC sweep. Choose
        Transient, AC, or DC sweep in the toolbar. Transient uses the ZMQ ngspice-server; the batch
        ngspice binary (NGSPICE_CLI or PATH) is only a fallback if ZMQ transient fails.
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: 10, background: "#1E1E1E" }}>
      {ac && (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 10,
              paddingBottom: 6,
              borderBottom: "1px solid #3C3C3C",
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: "bold",
                padding: "2px 10px",
                borderRadius: 3,
                background: "#264F78",
                color: "#B8D4F0",
              }}
            >
              AC SWEEP
            </span>
            <span style={{ fontSize: 12, color: "#AAA", fontFamily: "'Courier New',monospace" }}>
              {ac.frequency.length} pts | {(r.solve_time_ms || 0).toFixed(1)}ms
            </span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <DsoScope
              series={Object.keys(ac.magnitude || {}).map(function (k, i) {
                return {
                  x: ac.frequency,
                  y: (ac.magnitude[k] || []).map(function (v) {
                    return 20 * Math.log10(Math.max(Math.abs(v), 1e-30));
                  }),
                  label: k,
                  color: cl[i % 6],
                };
              })}
              logX={true}
              title="Magnitude (dB)"
              xLabel="Frequency (Hz)"
            />
            <DsoScope
              series={Object.keys(ac.phase_deg || {}).map(function (k, i) {
                return { x: ac.frequency, y: ac.phase_deg[k] || [], label: k, color: cl[i % 6] };
              })}
              logX={true}
              title="Phase (°)"
              xLabel="Frequency (Hz)"
            />
          </div>
        </div>
      )}
      {tr && (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 10,
              paddingBottom: 6,
              borderBottom: "1px solid #3C3C3C",
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: "bold",
                padding: "2px 10px",
                borderRadius: 3,
                background: "#5C4030",
                color: "#FFD4B0",
              }}
            >
              TRANSIENT
            </span>
            <span style={{ fontSize: 12, color: "#AAA", fontFamily: "'Courier New',monospace" }}>
              {tr.time.length} pts | {fe(tr.time[tr.time.length - 1], "s")} | {(r.solve_time_ms || 0).toFixed(1)}ms
            </span>
          </div>
          <DsoScope
            series={Object.keys(tr.vectors || {}).map(function (k, i) {
              return { x: tr.time, y: tr.vectors[k], label: k, color: cl[i % 6] };
            })}
            title="Time Domain"
            xLabel="Time (s)"
            h={270}
          />
        </div>
      )}
      {sw && (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 10,
              paddingBottom: 6,
              borderBottom: "1px solid #3C3C3C",
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: "bold",
                padding: "2px 10px",
                borderRadius: 3,
                background: "#4A3060",
                color: "#E0C8F0",
              }}
            >
              DC SWEEP
            </span>
            <span style={{ fontSize: 12, color: "#AAA", fontFamily: "'Courier New',monospace" }}>
              {sw.sweep_values.length} pts | {(r.solve_time_ms || 0).toFixed(1)}ms
            </span>
          </div>
          <DsoScope
            series={Object.keys(sw.vectors || {}).map(function (k, i) {
              return { x: sw.sweep_values, y: sw.vectors[k], label: k, color: cl[i % 5] };
            })}
            title="DC Transfer"
            xLabel="Sweep"
            h={270}
          />
        </div>
      )}
    </div>
  );
}
