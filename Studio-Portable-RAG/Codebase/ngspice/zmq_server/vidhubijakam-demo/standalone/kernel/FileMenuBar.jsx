import { useEffect, useRef, useState } from "react";

/** Classic File menu: load/save, edit, undo/redo, exit. */
export default function FileMenuBar(props) {
  var open = useState(false);
  var isOpen = open[0];
  var setOpen = open[1];
  var rootRef = useRef(null);

  useEffect(
    function () {
      if (!isOpen) return;
      function onDoc(ev) {
        if (rootRef.current && rootRef.current.contains(ev.target)) return;
        setOpen(false);
      }
      document.addEventListener("mousedown", onDoc);
      return function () {
        document.removeEventListener("mousedown", onDoc);
      };
    },
    [isOpen, setOpen],
  );

  function item(label, shortcut, onClick, disabled) {
    return (
      <button
        type="button"
        key={label}
        disabled={!!disabled}
        title={shortcut ? label + " (" + shortcut + ")" : label}
        onClick={function () {
          if (!disabled && onClick) onClick();
          setOpen(false);
        }}
        style={{
          display: "block",
          width: "100%",
          textAlign: "left",
          padding: "6px 14px",
          border: "none",
          background: disabled ? "#F0F0F0" : "#FFF",
          color: disabled ? "#AAA" : "#222",
          fontSize: 13,
          cursor: disabled ? "not-allowed" : "pointer",
        }}
        onMouseEnter={function (e) {
          if (!disabled) e.currentTarget.style.background = "#E3F2FD";
        }}
        onMouseLeave={function (e) {
          e.currentTarget.style.background = disabled ? "#F0F0F0" : "#FFF";
        }}
      >
        <span>{label}</span>
        {shortcut ? (
          <span style={{ float: "right", marginLeft: 16, color: "#888", fontSize: 11 }}>{shortcut}</span>
        ) : null}
      </button>
    );
  }

  function sep(k) {
    return <div key={k} style={{ height: 1, margin: "4px 0", background: "#DDD" }} />;
  }

  return (
    <div
      ref={rootRef}
      style={{
        flexShrink: 0,
        background: "#ECECEC",
        borderBottom: "1px solid #C0C0C0",
        padding: "0 8px",
        display: "flex",
        alignItems: "stretch",
        userSelect: "none",
        zIndex: 50,
      }}
    >
      <div style={{ position: "relative" }}>
        <button
          type="button"
          onClick={function () {
            setOpen(!isOpen);
          }}
          style={{
            padding: "5px 12px",
            border: "none",
            borderRight: "1px solid #D0D0D0",
            background: isOpen ? "#DDE8F5" : "transparent",
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 600,
            color: "#222",
          }}
        >
          File
        </button>
        {isOpen && (
          <div
            style={{
              position: "absolute",
              top: "100%",
              left: 0,
              minWidth: 220,
              background: "#FFF",
              border: "1px solid #B0B0B0",
              boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
              zIndex: 200,
              padding: "4px 0",
            }}
          >
            {item("Load circuit…", "Ctrl+O", props.onLoadCircuit, false)}
            {item("Save to User (Explorer)…", "Ctrl+S", props.onSaveCircuit, false)}
            {sep("a")}
            {item("Cut", "Ctrl+X", props.onCut, false)}
            {item("Copy", "Ctrl+C", props.onCopy, false)}
            {item("Paste", "Ctrl+V", props.onPaste, false)}
            {sep("b")}
            {item("Undo", "Ctrl+Z", props.onUndo, !props.canUndo)}
            {item("Redo", "Ctrl+Y", props.onRedo, !props.canRedo)}
            {sep("c")}
            {item("Exit", "", props.onExit, false)}
          </div>
        )}
      </div>
    </div>
  );
}
