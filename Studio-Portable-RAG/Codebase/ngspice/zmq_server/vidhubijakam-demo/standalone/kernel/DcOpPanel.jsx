import { fe } from "./formatValue.js";

export function shouldShowDcOpPanel(r) {
  if (!r) return false;
  return !!(r.dc_op || (!r.ac_sweep && !r.transient && !r.dc_sweep));
}

/** DC operating point header + Node Voltages / Branch Data tables (shared by editor and bottom tab). */
export default function DcOpPanel(props) {
  var r = props.r;
  var marginTop = props.marginTop != null ? props.marginTop : 0;
  if (!r || !shouldShowDcOpPanel(r)) return null;
  var dc = r.dc_op || {};
  var n = r.nodes || {};
  var co = r.components || {};
  var nv = dc.node_voltages || {};
  if (!Object.keys(nv).length)
    Object.entries(n).forEach(function (e) {
      nv[e[0]] = e[1] && typeof e[1] === "object" ? e[1].real : e[1];
    });
  var ne = Object.entries(nv)
    .filter(function (e) {
      return e[0] !== "0";
    })
    .sort();
  var ce = Object.entries(co);
  var th = {
    textAlign: "left",
    fontSize: 12,
    color: "#555",
    padding: "6px 8px",
    borderBottom: "2px solid #D0D0D0",
    fontWeight: 600,
    background: "#F5F5F5",
  };
  var td = { fontFamily: "'Courier New',monospace", fontSize: 12, padding: "5px 8px", borderBottom: "1px solid #EBEBEB" };
  var tv = Object.assign({}, td, { textAlign: "right", color: "#0060C0", fontWeight: "bold" });
  var card = { background: "#FFF", border: "1px solid #D8D8D8", borderRadius: 4, overflow: "hidden" };
  var ch = {
    fontSize: 11,
    fontWeight: 600,
    color: "#333",
    padding: "7px 10px",
    background: "#F8F8F8",
    borderBottom: "1px solid #E8E8E8",
  };
  return (
    <div style={{ marginTop: marginTop }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 10,
          paddingBottom: 6,
          borderBottom: "1px solid #E0E0E0",
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: "bold",
            padding: "2px 10px",
            borderRadius: 3,
            background: "#E8F5E9",
            color: "#2E7D32",
          }}
        >
          DC OP
        </span>
        <span style={{ fontSize: 12, color: "#666", fontFamily: "'Courier New',monospace" }}>
          {dc.converged !== false ? "Converged" : "FAILED"} | {dc.iterations || r.nr_iterations || 0} iter |{" "}
          {(r.solve_time_ms || 0).toFixed(1)}ms
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={card}>
          <div style={ch}>Node Voltages</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>Node</th>
                <th style={Object.assign({}, th, { textAlign: "right" })}>Voltage</th>
              </tr>
            </thead>
            <tbody>
              {ne.map(function (e) {
                return (
                  <tr key={e[0]}>
                    <td style={td}>{e[0]}</td>
                    <td style={tv}>{fe(e[1], "V")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div style={card}>
          <div style={ch}>Branch Data</div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={th}>ID</th>
                <th style={Object.assign({}, th, { textAlign: "right" })}>Current</th>
                <th style={Object.assign({}, th, { textAlign: "right" })}>Power</th>
              </tr>
            </thead>
            <tbody>
              {ce.map(function (e) {
                var c2 = e[1];
                return (
                  <tr key={e[0]}>
                    <td style={td}>{e[0]}</td>
                    <td style={tv}>
                      {fe(c2 && c2.current ? (c2.current.real != null ? c2.current.real : c2.current) : null, "A")}
                    </td>
                    <td style={tv}>
                      {fe(c2 && c2.power ? (c2.power.real != null ? c2.power.real : c2.power) : null, "W")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
