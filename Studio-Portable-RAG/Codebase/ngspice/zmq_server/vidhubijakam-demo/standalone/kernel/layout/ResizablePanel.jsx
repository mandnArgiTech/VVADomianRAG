import { useRef, useCallback } from "react";

/**
 * Read a persisted panel size from localStorage.
 * @param {string} key
 * @param {number} fallback
 * @param {number} minSize
 * @param {number} maxSize
 * @returns {number}
 */
export function readStoredPanelSize(key, fallback, minSize, maxSize) {
  try {
    var raw = localStorage.getItem(key);
    var n = parseFloat(raw);
    if (!isFinite(n)) return fallback;
    return Math.min(maxSize, Math.max(minSize, n));
  } catch (e) {
    return fallback;
  }
}

/**
 * Generic resizable panel: drag handle on one edge.
 * @param {{ direction: 'left'|'right'|'top'|'bottom', size: number, onResize: (n:number)=>void, minSize?: number, maxSize?: number, storageKey?: string, children?: import('react').ReactNode }} props
 */
export default function ResizablePanel(props) {
  var direction = props.direction || "right";
  var size = props.size;
  var onResize = props.onResize;
  var minSize = props.minSize != null ? props.minSize : 50;
  var maxSize = props.maxSize != null ? props.maxSize : 2000;
  var storageKey = props.storageKey;
  var children = props.children;

  var dragRef = useRef(null);
  var lastSizeRef = useRef(size);
  lastSizeRef.current = size;

  var clamp = useCallback(
    function (n) {
      return Math.min(maxSize, Math.max(minSize, n));
    },
    [minSize, maxSize],
  );

  var persist = useCallback(
    function (n) {
      if (!storageKey) return;
      try {
        localStorage.setItem(storageKey, String(Math.round(n)));
      } catch (e) {}
    },
    [storageKey],
  );

  var onPointerDown = useCallback(
    function (e) {
      if (e.button !== 0) return;
      e.preventDefault();
      var start = size;
      var sx = e.clientX;
      var sy = e.clientY;
      dragRef.current = { start: start, sx: sx, sy: sy };
      try {
        e.currentTarget.setPointerCapture(e.pointerId);
      } catch (err) {}
    },
    [size],
  );

  var onPointerMove = useCallback(
    function (e) {
      var d = dragRef.current;
      if (!d) return;
      var dx = e.clientX - d.sx;
      var dy = e.clientY - d.sy;
      var next = d.start;
      if (direction === "right") next = d.start + dx;
      else if (direction === "left") next = d.start - dx;
      else if (direction === "bottom") next = d.start + dy;
      else if (direction === "top") next = d.start - dy;
      var c = clamp(next);
      lastSizeRef.current = c;
      onResize(c);
    },
    [direction, onResize, clamp],
  );

  var onPointerUp = useCallback(
    function (e) {
      var was = !!dragRef.current;
      dragRef.current = null;
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch (err) {}
      if (was) persist(lastSizeRef.current);
    },
    [persist],
  );

  var handleStyle = {
    flexShrink: 0,
    background: "#D8D8D8",
    zIndex: 5,
  };
  if (direction === "left" || direction === "right") {
    Object.assign(handleStyle, {
      width: 4,
      cursor: "col-resize",
      borderLeft: "1px solid #B0B0B0",
      borderRight: "1px solid #B0B0B0",
    });
  } else {
    Object.assign(handleStyle, {
      height: 4,
      cursor: "row-resize",
      borderTop: "1px solid #B0B0B0",
      borderBottom: "1px solid #B0B0B0",
    });
  }

  var handle = (
    <div
      role="separator"
      aria-orientation={direction === "left" || direction === "right" ? "vertical" : "horizontal"}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      style={handleStyle}
    />
  );

  if (direction === "right") {
    return (
      <div style={{ display: "flex", flexDirection: "row", height: "100%", minHeight: 0, minWidth: 0 }}>
        <div
          style={{
            width: size,
            minWidth: size,
            maxWidth: size,
            height: "100%",
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {children}
        </div>
        {handle}
      </div>
    );
  }

  if (direction === "left") {
    return (
      <div style={{ display: "flex", flexDirection: "row", height: "100%", minHeight: 0, minWidth: 0 }}>
        {handle}
        <div
          style={{
            width: size,
            minWidth: size,
            maxWidth: size,
            height: "100%",
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {children}
        </div>
      </div>
    );
  }

  if (direction === "top") {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
          height: size,
          minHeight: size,
          maxHeight: size,
          minWidth: 0,
          overflow: "hidden",
        }}
      >
        {handle}
        <div style={{ flex: 1, minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>{children}</div>
      </div>
    );
  }

  /* bottom */
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        height: size,
        minHeight: size,
        maxHeight: size,
        minWidth: 0,
        overflow: "hidden",
      }}
    >
      <div style={{ flex: 1, minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>{children}</div>
      {handle}
    </div>
  );
}
