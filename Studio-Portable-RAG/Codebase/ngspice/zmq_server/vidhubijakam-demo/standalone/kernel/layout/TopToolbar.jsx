/**
 * Consolidated top toolbar: branding, kernel/API, DRC/Run/analysis, AI/library badges, shortcut legend.
 * @param {{
 *   catalogCount: number,
 *   apiOpen: boolean,
 *   onToggleApi: () => void,
 *   kernelBoot: string,
 *   kernelStep: string,
 *   an: string,
 *   setAn: (v: string) => void,
 *   onRun: () => void,
 *   onDRC: () => void,
 *   busy: boolean,
 *   aiKey: string,
 *   onNeedAiKey: () => void,
 *   libStatus: string,
 *   libBar: string,
 *   libMsg: string,
 *   simN: number,
 *   lineCount: number,
 * }} props
 */
export default function TopToolbar(props) {
  var catalogCount = props.catalogCount != null ? props.catalogCount : 0;
  var apiOpen = !!props.apiOpen;
  var onToggleApi = props.onToggleApi || function () {};
  var kernelBoot = props.kernelBoot || "loading";
  var kernelStep = props.kernelStep || "";
  var an = props.an || "op";
  var setAn = props.setAn || function () {};
  var onRun = props.onRun || function () {};
  var onDRC = props.onDRC || function () {};
  var busy = !!props.busy;
  var aiKey = props.aiKey || "";
  var onNeedAiKey = props.onNeedAiKey || function () {};
  var libStatus = props.libStatus || "idle";
  var libBar = props.libBar || "";
  var libMsg = props.libMsg || "";
  var simN = props.simN != null ? props.simN : 0;
  var lineCount = props.lineCount != null ? props.lineCount : 0;

  var kernelBadge = {
    fontSize: 10,
    padding: "2px 8px",
    borderRadius: 3,
    fontFamily: "'Segoe UI',sans-serif",
    fontWeight: 600,
    border: "1px solid",
    whiteSpace: "nowrap",
  };
  if (kernelBoot === "ready") Object.assign(kernelBadge, { background: "#E8F5E9", color: "#2E7D32", borderColor: "#A5D6A7" });
  else if (kernelBoot === "starting") Object.assign(kernelBadge, { background: "#FFF3E0", color: "#E65100", borderColor: "#FFCC80" });
  else if (kernelBoot === "offline") Object.assign(kernelBadge, { background: "#FFEBEE", color: "#C62828", borderColor: "#FFCDD2" });
  else Object.assign(kernelBadge, { background: "#E3F2FD", color: "#1565C0", borderColor: "#90CAF9" });
  /* NodalAI used "Starting" for engine boot; here `ready:false` usually means waiting for ZMQ/ngspice-server. */
  var kernelLabel =
    "Kernel: " +
    (kernelBoot === "ready"
      ? "Ready"
      : kernelBoot === "starting"
      ? "Waiting for engine"
      : kernelBoot === "offline"
      ? "Offline"
      : "...");

  var aiBadge = {
    fontSize: 10,
    padding: "2px 8px",
    borderRadius: 3,
    fontFamily: "'Segoe UI',sans-serif",
    fontWeight: 600,
    border: "1px solid",
    whiteSpace: "nowrap",
    cursor: !String(aiKey).trim() ? "pointer" : "default",
  };
  if (String(aiKey).trim()) Object.assign(aiBadge, { background: "#E8F5E9", color: "#2E7D32", borderColor: "#A5D6A7" });
  else Object.assign(aiBadge, { background: "#F5F5F5", color: "#9E9E9E", borderColor: "#E0E0E0" });
  var aiLabel = "AI: " + (String(aiKey).trim() ? "Ready" : "Offline");

  var kbd = {
    fontFamily: "'Courier New',monospace",
    background: "#EEE",
    padding: "1px 5px",
    borderRadius: 2,
    border: "1px solid #CCC",
  };

  return (
    <div style={{ flexShrink: 0, borderBottom: "1px solid #C0C0C0" }}>
      <div
        style={{
          background: "#E8E8E8",
          borderBottom: "1px solid #C0C0C0",
          padding: "0 16px",
          display: "flex",
          alignItems: "center",
          height: 34,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 20 }}>
          <div
            style={{
              width: 20,
              height: 20,
              background: "linear-gradient(135deg,#1565C0,#2E7D32)",
              borderRadius: 3,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 10,
              color: "#FFF",
            }}
          >
            V
          </div>
          <span style={{ fontSize: 13, fontWeight: 600 }}>VidhuBijakam</span>
          <span style={{ fontSize: 11, color: "#888" }}>SPICE Kernel</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "#666" }}>
          <span title={kernelStep || "GET /api/boot/status"} style={kernelBadge}>
            {kernelLabel}
          </span>
          <span>{catalogCount} circuits</span>
          <span
            style={{ cursor: "pointer", color: "#888", textDecoration: "underline" }}
            onClick={function () {
              onToggleApi();
            }}
          >
            API
          </span>
        </div>
      </div>
      <div
        style={{
          background: "#F0F0F0",
          borderBottom: "1px solid #D0D0D0",
          padding: "3px 16px",
          display: "flex",
          alignItems: "center",
          gap: 6,
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={onDRC}
          style={{
            fontSize: 11,
            padding: "3px 10px",
            borderRadius: 3,
            border: "1px solid #B0B0B0",
            background: "#FFF",
            color: "#333",
            cursor: "pointer",
          }}
        >
          DRC
        </button>
        <div style={{ width: 1, height: 18, background: "#C0C0C0" }} />
        <select
          value={an}
          onChange={function (e) {
            setAn(e.target.value);
          }}
          style={{
            fontSize: 12,
            padding: "2px 6px",
            borderRadius: 3,
            border: "1px solid #B0B0B0",
            background: "#FFF",
            cursor: "pointer",
          }}
        >
          <option value="op">DC OP</option>
          <option value="ac">AC Sweep</option>
          <option value="tran">Transient</option>
          <option value="dc">DC Sweep</option>
        </select>
        <button
          onClick={onRun}
          disabled={busy}
          style={{
            fontSize: 11,
            padding: "3px 14px",
            borderRadius: 3,
            border: "1px solid " + (busy ? "#CCC" : "#2E7D32"),
            background: busy ? "#E0E0E0" : "#2E7D32",
            color: busy ? "#999" : "#FFF",
            cursor: busy ? "not-allowed" : "pointer",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          {busy && (
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                border: "2px solid #CCC",
                borderTopColor: "#2E7D32",
                borderRadius: "50%",
                animation: "sp .5s linear infinite",
              }}
            />
          )}
          Run (F5)
        </button>
        <div style={{ width: 1, height: 18, background: "#C0C0C0" }} />
        <span
          title={
            String(aiKey).trim()
              ? "DeepSeek key set (sent to /api/ai/generate only)"
              : "Set DEEP_SEEK_API_KEY in .env or paste key below"
          }
          style={aiBadge}
          onClick={function () {
            if (!String(aiKey).trim()) onNeedAiKey();
          }}
        >
          {aiLabel}
        </span>
        {!String(aiKey).trim() && (
          <span
            style={{ fontSize: 10, color: "#C06000", cursor: "pointer", textDecoration: "underline" }}
            onClick={function () {
              onNeedAiKey();
            }}
          >
            Set key
          </span>
        )}
        <div style={{ width: 1, height: 18, background: "#C0C0C0" }} />
        <span
          title={libMsg || libBar}
          style={{
            fontSize: 10,
            color: libStatus === "ready" ? "#2E7D32" : libStatus === "loading" ? "#1565C0" : "#888",
            background: "#F5F5F5",
            padding: "2px 8px",
            borderRadius: 3,
            border: "1px solid #E0E0E0",
            fontFamily: "'Courier New',monospace",
            maxWidth: 280,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {libBar}
        </span>
        <div style={{ marginLeft: "auto", fontSize: 11, color: "#888", fontFamily: "'Courier New',monospace" }}>
          {lineCount} ln{simN > 0 ? " | " + simN + " runs" : ""}
        </div>
      </div>
      <div
        style={{
          background: "#FAFAFA",
          borderBottom: apiOpen ? "none" : "1px solid #E0E0E0",
          padding: "4px 16px",
          fontSize: 10,
          color: "#555",
          fontFamily: "'Segoe UI',sans-serif",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "6px 14px",
        }}
      >
        <span style={{ fontWeight: 700, color: "#78909C", marginRight: 4 }}>Shortcuts</span>
        <span>
          <kbd style={kbd}>F5</kbd> Run
        </span>
        <span>
          <kbd style={kbd}>Ctrl+D</kbd> DRC
        </span>
        <span>
          <kbd style={kbd}>Ctrl+I</kbd> / <kbd style={kbd}>Ctrl+K</kbd> AI
        </span>
        <span>
          <kbd style={kbd}>Ctrl+L</kbd> Library
        </span>
        <span>
          <kbd style={kbd}>Ctrl+Space</kbd> Autocomplete
        </span>
        <span>
          <kbd style={kbd}>Esc</kbd> Close popups
        </span>
      </div>
    </div>
  );
}
