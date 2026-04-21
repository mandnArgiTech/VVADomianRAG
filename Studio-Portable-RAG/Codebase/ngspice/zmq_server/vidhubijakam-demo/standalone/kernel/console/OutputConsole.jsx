import { useEffect, useRef } from "react";

/**
 * Scrollable monospace output log.
 * @param {{ entries: Array<{ ts: number, level: 'info'|'warn'|'error'|'success'|'diag', text: string }> }} props
 */
export default function OutputConsole(props) {
  var entries = props.entries || [];
  var bottomRef = useRef(null);

  useEffect(
    function () {
      var el = bottomRef.current;
      if (el) el.scrollIntoView({ block: "end" });
    },
    [entries.length],
  );

  var levelColor = function (level) {
    if (level === "error") return "#F48771";
    if (level === "warn") return "#CCA700";
    if (level === "success") return "#89D185";
    if (level === "diag") return "#4EC9B0";
    return "#CCCCCC";
  };

  var pad2 = function (n) {
    return (n < 10 ? "0" : "") + n;
  };
  var fmtTs = function (ts) {
    var d = new Date(ts);
    return pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds());
  };

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        background: "#1E1E1E",
        color: "#D4D4D4",
        fontFamily: "'Consolas','Courier New',monospace",
        fontSize: 12,
        lineHeight: 1.45,
        padding: "8px 10px",
      }}
    >
      {entries.map(function (e, i) {
        return (
          <div key={i} style={{ marginBottom: 2, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            <span style={{ color: "#858585", marginRight: 8 }}>{fmtTs(e.ts)}</span>
            <span style={{ color: levelColor(e.level), marginRight: 8, fontWeight: 700, textTransform: "uppercase", fontSize: 10 }}>
              [{e.level}]
            </span>
            <span style={{ color: "#D4D4D4" }}>{e.text}</span>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
