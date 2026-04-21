import DcOpPanel, { shouldShowDcOpPanel } from "./DcOpPanel.jsx";

/** DC operating point view for the bottom tool window. */
export default function DcOpSimulationTab(props) {
  var r = props.r;
  var emptyStyle = {
    flex: 1,
    minHeight: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "'Segoe UI',sans-serif",
    fontSize: 13,
  };
  if (!r) {
    return (
      <div style={Object.assign({}, emptyStyle, { background: "#ECECEC", color: "#666" })}>
        Run a simulation to see DC operating point results.
      </div>
    );
  }
  if (!shouldShowDcOpPanel(r)) {
    return (
      <div
        style={Object.assign({}, emptyStyle, {
          background: "#ECECEC",
          color: "#666",
          padding: 16,
          textAlign: "center",
        })}
      >
        No DC operating point for this run (e.g. AC, transient, or DC sweep only). Use OP / DC analysis to
        populate Node Voltages and Branch Data.
      </div>
    );
  }
  return (
    <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: 10, background: "#ECECEC" }}>
      <DcOpPanel r={r} marginTop={0} />
    </div>
  );
}
