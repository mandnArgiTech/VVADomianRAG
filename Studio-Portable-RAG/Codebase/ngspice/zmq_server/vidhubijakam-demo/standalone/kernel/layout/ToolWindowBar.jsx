/**
 * Thin IntelliJ-style tool window strip (left or bottom edge).
 * @param {{ direction: 'left'|'bottom', items: Array<{ id: string, icon?: string, label: string, active?: boolean }>, onToggle: (id: string)=>void }} props
 */
export default function ToolWindowBar(props) {
  var direction = props.direction || "left";
  var items = props.items || [];
  var onToggle = props.onToggle || function () {};

  var isVert = direction === "left";
  var barStyle = {
    flexShrink: 0,
    background: "#E4E4E4",
    borderRight: isVert ? "1px solid #C0C0C0" : undefined,
    borderTop: !isVert ? "1px solid #C0C0C0" : undefined,
    display: "flex",
    flexDirection: isVert ? "column" : "row",
    alignItems: "center",
    gap: isVert ? 2 : 0,
    padding: isVert ? "6px 0" : "0 6px",
    width: isVert ? 28 : "auto",
    height: isVert ? "auto" : 28,
    minWidth: isVert ? 28 : 0,
    minHeight: !isVert ? 28 : 0,
    boxSizing: "border-box",
  };

  return (
    <div style={barStyle} role="toolbar" aria-label="Tool windows">
      {items.map(function (it) {
        var act = !!it.active;
        return (
          <button
            key={it.id}
            type="button"
            title={it.label}
            onClick={function () {
              onToggle(it.id);
            }}
            style={{
              border: "none",
              background: act ? "#D0E8FF" : "transparent",
              color: "#333",
              cursor: "pointer",
              width: isVert ? 26 : "auto",
              height: isVert ? 26 : 26,
              minWidth: !isVert ? 32 : 26,
              padding: isVert ? 0 : "0 6px",
              margin: isVert ? "1px 1px" : "1px 2px",
              borderRadius: 3,
              fontSize: isVert ? 14 : 11,
              fontWeight: act ? 700 : 500,
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "'Segoe UI',sans-serif",
            }}
          >
            {act && (
              <span
                style={{
                  position: "absolute",
                  background: "#0E639C",
                  borderRadius: 1,
                  ...(isVert
                    ? { left: 1, top: 4, bottom: 4, width: 3 }
                    : { top: 1, left: 4, right: 4, height: 3 }),
                }}
              />
            )}
            <span style={{ position: "relative", zIndex: 1 }}>{it.icon || it.label.charAt(0)}</span>
          </button>
        );
      })}
    </div>
  );
}
