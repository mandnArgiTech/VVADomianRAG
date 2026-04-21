/**
 * Placeholder schematic view (future NodalAI / canvas integration).
 * @param {{ net?: string }} props
 */
export default function SchematicCanvas(props) {
  void props.net;
  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#252526",
        color: "#888",
        fontFamily: "'Segoe UI',sans-serif",
        fontSize: 14,
      }}
    >
      Schematic view — coming soon
    </div>
  );
}
