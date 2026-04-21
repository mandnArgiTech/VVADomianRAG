/**
 * Multi-tab bar above the editor.
 * @param {{
 *   tabs: Array<{ id: string, label: string, dirty?: boolean }>,
 *   activeId: string,
 *   onSelect: (id: string) => void,
 *   onClose: (id: string) => void,
 *   onAdd: () => void,
 * }} props
 */
export default function EditorTabBar(props) {
  var tabs = props.tabs || [];
  var activeId = props.activeId;
  var onSelect = props.onSelect || function () {};
  var onClose = props.onClose || function () {};
  var onAdd = props.onAdd || function () {};

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "stretch",
        flexShrink: 0,
        background: "#E4E4E4",
        borderBottom: "1px solid #C0C0C0",
        minHeight: 30,
        paddingLeft: 4,
        gap: 2,
      }}
    >
      {tabs.map(function (t) {
        var sel = t.id === activeId;
        return (
          <div
            key={t.id}
            role="tab"
            aria-selected={sel}
            onClick={function () {
              onSelect(t.id);
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              maxWidth: 200,
              cursor: "pointer",
              background: sel ? "#F2F2F2" : "#D8D8D8",
              border: "1px solid " + (sel ? "#C0C0C0" : "#C8C8C8"),
              borderBottom: sel ? "1px solid #F2F2F2" : "1px solid #C8C8C8",
              marginBottom: sel ? -1 : 0,
              borderRadius: "4px 4px 0 0",
              fontSize: 12,
              fontFamily: "'Segoe UI',sans-serif",
              color: sel ? "#333" : "#555",
              fontWeight: sel ? 600 : 400,
              userSelect: "none",
            }}
          >
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{t.label}</span>
            {t.dirty ? <span style={{ color: "#1565C0", fontSize: 14, lineHeight: 1 }} title="Modified">{"\u2022"}</span> : null}
            {tabs.length > 1 ? (
              <button
                type="button"
                title="Close"
                onClick={function (e) {
                  e.stopPropagation();
                  onClose(t.id);
                }}
                style={{
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 14,
                  lineHeight: 1,
                  padding: "0 2px",
                  color: "#666",
                }}
              >
                {"\u00D7"}
              </button>
            ) : null}
          </div>
        );
      })}
      <button
        type="button"
        title="New tab"
        onClick={onAdd}
        style={{
          alignSelf: "center",
          marginLeft: 4,
          width: 24,
          height: 22,
          border: "1px solid #B0B0B0",
          borderRadius: 3,
          background: "#FFF",
          cursor: "pointer",
          fontSize: 16,
          lineHeight: 1,
          color: "#333",
        }}
      >
        +
      </button>
    </div>
  );
}
