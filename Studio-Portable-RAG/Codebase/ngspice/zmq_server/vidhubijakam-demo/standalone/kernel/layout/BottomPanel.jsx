/**
 * Tabbed bottom tool window (IntelliJ-style).
 * @param {{ tabs: Array<{ id: string, label: string, content: import('react').ReactNode }>, activeTab: string, onTabChange: (id: string)=>void }} props
 */
export default function BottomPanel(props) {
  var tabs = props.tabs || [];
  var activeTab = props.activeTab;
  var onTabChange = props.onTabChange || function () {};

  var active = tabs.find(function (t) {
    return t.id === activeTab;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0, background: "#F0F0F0", borderTop: "1px solid #C0C0C0" }}>
      <div
        role="tablist"
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "stretch",
          flexShrink: 0,
          background: "#E8E8E8",
          borderBottom: "1px solid #C8C8C8",
          minHeight: 28,
        }}
      >
        {tabs.map(function (t) {
          var sel = t.id === activeTab;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={sel}
              onClick={function () {
                onTabChange(t.id);
              }}
              style={{
                border: "none",
                borderRight: "1px solid #C0C0C0",
                borderBottom: sel ? "2px solid #0E639C" : "2px solid transparent",
                marginBottom: sel ? -1 : 0,
                padding: "4px 14px",
                fontSize: 12,
                fontFamily: "'Segoe UI',sans-serif",
                fontWeight: sel ? 600 : 400,
                color: sel ? "#0E639C" : "#555",
                background: sel ? "#F8F8F8" : "#E4E4E4",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        style={{
          flex: 1,
          minHeight: 0,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          background: "#1E1E1E",
        }}
      >
        {active ? active.content : null}
      </div>
    </div>
  );
}
