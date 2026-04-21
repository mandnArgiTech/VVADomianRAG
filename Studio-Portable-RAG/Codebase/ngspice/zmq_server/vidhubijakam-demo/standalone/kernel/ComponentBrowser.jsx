/**
 * Floating component library browser (D5EX-88C): Ctrl+L from KernelNetlistEditor.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { searchLocal, searchRemote, getTypes, getPartDetail } from "../libraryCache.js";
import { generateSpiceForPart, buildInsertBlock, insertSingleLineAtLine, appendModelsBeforeEnd } from "../spiceInsert.js";
import { normalizeApiBase } from "./apiConfig.js";
import { formatPartBrief } from "./spiceAutocomplete.js";

var PARENT_ORDER = [
  "MOSFET",
  "SiC_MOSFET",
  "BJT",
  "DIODE",
  "RESISTOR",
  "CAPACITOR",
  "INDUCTOR",
  "IGBT",
  "LED",
  "JFET",
  "OPAMP",
];

function parentBucketForApiType(t) {
  var u = String(t || "").toUpperCase();
  if (u.indexOf("JFET") >= 0 || u.indexOf("NJF") >= 0 || u.indexOf("PJF") >= 0) return "JFET";
  if (u.indexOf("SIC") >= 0 && (u.indexOf("MOS") >= 0 || u.indexOf("FET") >= 0)) return "SiC_MOSFET";
  if (u.indexOf("OPAMP") >= 0 || u.indexOf("OP_AMP") >= 0 || u === "OPAMP") return "OPAMP";
  if (u.indexOf("IGBT") >= 0) return "IGBT";
  if (u.indexOf("LED") >= 0) return "LED";
  if (u.indexOf("NPN") >= 0 || u.indexOf("PNP") >= 0 || u.indexOf("BJT") >= 0) return "BJT";
  if (u.indexOf("ZENER") >= 0 || u.indexOf("SCHOTTKY") >= 0 || u.indexOf("DIODE") >= 0 || u === "D")
    return "DIODE";
  if (u.indexOf("MOS") >= 0 || u === "NMOS" || u === "PMOS") return "MOSFET";
  if (u.indexOf("RES") >= 0 || u === "R") return "RESISTOR";
  if (u.indexOf("CAP") >= 0 || u === "C") return "CAPACITOR";
  if (u.indexOf("IND") >= 0 || u === "L") return "INDUCTOR";
  return "OTHER";
}

function bucketLabel(key) {
  if (key === "OTHER") return "Other";
  return key.replace(/_/g, " ");
}

/** Types from count-by-type that fall in this parent bucket. */
function apiTypesInBucket(bucket, typeRows) {
  var out = [];
  for (var i = 0; i < typeRows.length; i++) {
    var t = typeRows[i].type;
    if (parentBucketForApiType(t) === bucket) out.push(t);
  }
  return out;
}

function rowMatchesMosNch(r) {
  var c = String(r.comp_type || "").toUpperCase();
  return c.indexOf("MOSFET_N") >= 0 || c.indexOf("NMOS") >= 0 || (c.indexOf("N-CH") >= 0 && c.indexOf("MOS") >= 0);
}

function rowMatchesMosPch(r) {
  var c = String(r.comp_type || "").toUpperCase();
  return c.indexOf("MOSFET_P") >= 0 || c.indexOf("PMOS") >= 0 || c.indexOf("P-CH") >= 0;
}

function rowMatchesNpn(r) {
  var c = String(r.comp_type || "").toUpperCase();
  return c.indexOf("BJT_NPN") >= 0 || c.indexOf("NPN") >= 0;
}

function rowMatchesPnp(r) {
  var c = String(r.comp_type || "").toUpperCase();
  return c.indexOf("BJT_PNP") >= 0 || c.indexOf("PNP") >= 0;
}

/** Best-effort diode subfamily when catalog uses coarse DIODE type (see D5EX-88C). */
function rowMatchesDiodeSub(r, sub) {
  var c = String(r.comp_type || "").toUpperCase();
  var d = String(r.description || "").toLowerCase();
  if (sub === "d_sch")
    return c.indexOf("SCHOTTKY") >= 0 || d.indexOf("schottky") >= 0;
  if (sub === "d_zen") return c.indexOf("ZENER") >= 0 || d.indexOf("zener") >= 0;
  if (sub === "d_rect") {
    if (c.indexOf("ZENER") >= 0 || c.indexOf("SCHOTTKY") >= 0) return false;
    if (d.indexOf("zener") >= 0 || d.indexOf("schottky") >= 0) return false;
    return true;
  }
  return true;
}

function applySubFilter(row, bucket, sub) {
  if (!sub) return true;
  if (bucket === "MOSFET") {
    if (sub === "nch") return rowMatchesMosNch(row);
    if (sub === "pch") return rowMatchesMosPch(row);
  }
  if (bucket === "BJT") {
    if (sub === "npn") return rowMatchesNpn(row);
    if (sub === "pnp") return rowMatchesPnp(row);
  }
  if (bucket === "DIODE") {
    return rowMatchesDiodeSub(row, sub);
  }
  return true;
}

function countForBucket(bucket, typeRows) {
  var types = apiTypesInBucket(bucket, typeRows);
  var n = 0;
  for (var i = 0; i < types.length; i++) {
    for (var j = 0; j < typeRows.length; j++) {
      if (typeRows[j].type === types[i]) n += typeRows[j].count || 0;
    }
  }
  return n;
}

/**
 * @param {object} props
 * @param {boolean} props.visible
 * @param {{ x: number, y: number }} props.position
 * @param {number} props.insertAtLine1Based — 1-based line index for insert
 * @param {string} props.netlist
 * @param {object|null} props.libCache — LibraryCache from initLibraryCache
 * @param {string} props.apiBase
 * @param {() => void} props.onClose
 * @param {string} [props.seedCompType] — when opening from AI, prefer this comp_type
 */
export default function ComponentBrowser(props) {
  var visible = props.visible;
  var libCache = props.libCache;
  var apiBase = props.apiBase;
  var netlist = props.netlist || "";
  var onClose = props.onClose;
  var insertAtLine1Based = props.insertAtLine1Based || 1;
  var position = props.position || { x: 80, y: 120 };
  var setNet = props.setNet;
  var seedCompType = props.seedCompType;

  var _q = useState(""),
    pickQ = _q[0],
    setPickQ = _q[1];
  var _sel = useState({ all: true, bucket: null, sub: null, singleType: null }),
    treeSel = _sel[0],
    setTreeSel = _sel[1];
  var _exp = useState({}),
    expanded = _exp[0],
    setExpanded = _exp[1];
  var _pr = useState([]),
    pickAllResults = _pr[0],
    setPickAllResults = _pr[1];
  var _psi = useState(0),
    pickSel = _psi[0],
    setPickSel = _psi[1];
  var _pm = useState("All"),
    pickMfr = _pm[0],
    setPickMfr = _pm[1];
  var _pbusy = useState(false),
    pickBusy = _pbusy[0],
    setPickBusy = _pbusy[1];
  var _pml = useState(["All"]),
    pickMfrList = _pml[0],
    setPickMfrList = _pml[1];
  var _closing = useState(false),
    closing = _closing[0],
    setClosing = _closing[1];
  var _searchFocus = useState(false),
    searchFocused = _searchFocus[0],
    setSearchFocused = _searchFocus[1];

  var pickSearchRef = useRef(null);
  var resultsListRef = useRef(null);
  var insertBtnRef = useRef(null);
  var pickSearchTRef = useRef(null);

  var typeRows = useMemo(
    function () {
      return getTypes(libCache);
    },
    [libCache],
  );

  var treeParents = useMemo(
    function () {
      var rows = [];
      for (var i = 0; i < PARENT_ORDER.length; i++) {
        var b = PARENT_ORDER[i];
        var cnt = countForBucket(b, typeRows);
        if (cnt <= 0) continue;
        var subs = [];
        if (b === "MOSFET") {
          subs.push({ key: "nch", label: "N-channel" });
          subs.push({ key: "pch", label: "P-channel" });
        } else if (b === "BJT") {
          subs.push({ key: "npn", label: "NPN" });
          subs.push({ key: "pnp", label: "PNP" });
        } else if (b === "DIODE") {
          subs.push({ key: "d_rect", label: "Rectifier" });
          subs.push({ key: "d_sch", label: "Schottky" });
          subs.push({ key: "d_zen", label: "Zener" });
        }
        rows.push({ bucket: b, label: bucketLabel(b), count: cnt, subs: subs });
      }
      var otherTypes = typeRows.filter(function (tr) {
        return parentBucketForApiType(tr.type) === "OTHER";
      });
      for (var oi = 0; oi < otherTypes.length; oi++) {
        rows.push({
          bucket: "_ONE_" + otherTypes[oi].type,
          label: otherTypes[oi].type,
          count: otherTypes[oi].count,
          subs: [],
          singleType: otherTypes[oi].type,
        });
      }
      return rows;
    },
    [typeRows],
  );

  var primaryBrowseType = useMemo(
    function () {
      if (treeSel.all) {
        var ts = getTypes(libCache);
        return ts.length ? ts[0].type : "";
      }
      if (treeSel.bucket && String(treeSel.bucket).indexOf("_ONE_") === 0) return treeSel.singleType || "";
      var list = apiTypesInBucket(treeSel.bucket, typeRows);
      return list.length ? list[0] : "";
    },
    [treeSel, libCache, typeRows],
  );

  var remoteCompType = useMemo(
    function () {
      if (treeSel.all) return "";
      if (treeSel.bucket && String(treeSel.bucket).indexOf("_ONE_") === 0) return treeSel.singleType || "";
      var list = apiTypesInBucket(treeSel.bucket, typeRows);
      if (list.length === 1) return list[0];
      return "";
    },
    [treeSel, typeRows],
  );

  var resultRowFilter = useCallback(
    function (row) {
      if (treeSel.all) return true;
      if (treeSel.bucket && String(treeSel.bucket).indexOf("_ONE_") === 0) {
        return String(row.comp_type || "") === treeSel.singleType;
      }
      var allowed = apiTypesInBucket(treeSel.bucket, typeRows);
      var ct = String(row.comp_type || "");
      if (allowed.indexOf(ct) < 0) return false;
      return applySubFilter(row, treeSel.bucket, treeSel.sub);
    },
    [treeSel, typeRows],
  );

  var pickDisplay = useMemo(
    function () {
      var rows =
        pickMfr === "All"
          ? pickAllResults
          : pickAllResults.filter(function (r) {
              return (r.manufacturer || "") === pickMfr;
            });
      return rows.filter(resultRowFilter);
    },
    [pickAllResults, pickMfr, resultRowFilter],
  );

  useEffect(
    function () {
      if (!visible) return;
      setClosing(false);
      setPickQ("");
      setPickSel(0);
      setPickMfr("All");
      setExpanded({});
      if (seedCompType && String(seedCompType).trim()) {
        var sc = String(seedCompType).trim();
        var b = parentBucketForApiType(sc);
        if (b === "OTHER") setTreeSel({ all: false, bucket: "_ONE_" + sc, sub: null, singleType: sc });
        else setTreeSel({ all: false, bucket: b, sub: null, singleType: null });
      } else {
        var ts = getTypes(libCache);
        if (ts.length) {
          var b0 = parentBucketForApiType(ts[0].type);
          if (b0 === "OTHER")
            setTreeSel({ all: false, bucket: "_ONE_" + ts[0].type, sub: null, singleType: ts[0].type });
          else setTreeSel({ all: false, bucket: b0, sub: null, singleType: null });
        } else setTreeSel({ all: true, bucket: null, sub: null, singleType: null });
      }
      setTimeout(function () {
        if (pickSearchRef.current) pickSearchRef.current.focus();
      }, 60);
    },
    [visible, seedCompType, libCache],
  );

  useEffect(
    function () {
      setPickSel(function (s) {
        var mx = Math.max(pickDisplay.length - 1, 0);
        return Math.min(Math.max(s, 0), mx);
      });
    },
    [pickDisplay.length, pickMfr],
  );

  useEffect(
    function () {
      if (pickMfrList.indexOf(pickMfr) < 0) setPickMfr("All");
    },
    [pickMfrList, pickMfr],
  );

  useEffect(
    function () {
      if (!visible) return;
      clearTimeout(pickSearchTRef.current);
      setPickBusy(true);
      pickSearchTRef.current = setTimeout(function () {
        var q = pickQ.trim();
        var t = remoteCompType;
        var local = [];
        var cacheReady = libCache && libCache.ready;
        if (cacheReady) {
          if (q.length >= 2) local = searchLocal(libCache, q, { limit: 40 });
          else if (primaryBrowseType) local = (libCache.topParts[primaryBrowseType] || []).slice();
          if (t) local = local.filter(function (r) {
            return String(r.comp_type || "") === t;
          });
          if (!treeSel.all && treeSel.bucket && String(treeSel.bucket).indexOf("_ONE_") !== 0) {
            var allowed = apiTypesInBucket(treeSel.bucket, typeRows);
            local = local.filter(function (r) {
              return allowed.indexOf(String(r.comp_type || "")) >= 0;
            });
            local = local.filter(function (r) {
              return applySubFilter(r, treeSel.bucket, treeSel.sub);
            });
          }
          if (treeSel.bucket && String(treeSel.bucket).indexOf("_ONE_") === 0) {
            var st = treeSel.singleType;
            local = local.filter(function (r) {
              return String(r.comp_type || "") === st;
            });
          }
        }
        var wantRemote =
          !cacheReady ||
          q.length >= 3 ||
          (q.length >= 2 && local.length < 4) ||
          (q.length < 2 && !t) ||
          (q.length < 2 && !!t && local.length === 0);
        var root = normalizeApiBase(apiBase);
        var p1 = wantRemote ? searchRemote(root, q, t || "", 40) : Promise.resolve([]);
        p1
          .then(function (remote) {
            var seen = {};
            var comb = [];
            function add(r) {
              var pn = r && r.part_number;
              if (!pn || seen[pn]) return;
              seen[pn] = 1;
              comb.push(r);
            }
            local.forEach(add);
            (remote || []).forEach(add);
            comb = comb.filter(resultRowFilter);
            var mfrs = {};
            comb.forEach(function (r) {
              if (r.manufacturer) mfrs[r.manufacturer] = 1;
            });
            var opts = ["All"].concat(Object.keys(mfrs).sort());
            setPickMfrList(opts);
            setPickAllResults(comb);
            setPickSel(0);
          })
          .catch(function () {
            setPickAllResults([]);
          })
          .finally(function () {
            setPickBusy(false);
          });
      }, 150);
      return function () {
        clearTimeout(pickSearchTRef.current);
      };
    },
    [
      visible,
      pickQ,
      remoteCompType,
      primaryBrowseType,
      apiBase,
      libCache,
      treeSel,
      typeRows,
      resultRowFilter,
    ],
  );

  var insertSelection = useCallback(
    function () {
      var row = pickDisplay[pickSel];
      if (!row || !setNet) return;
      setPickBusy(true);
      var root = normalizeApiBase(apiBase);
      getPartDetail(root, row.part_number)
        .then(function (det) {
          var r = det || row;
          var blk = buildInsertBlock(netlist, r);
          var withInst = insertSingleLineAtLine(netlist, Math.max(0, insertAtLine1Based - 1), blk.instanceLine);
          setNet(appendModelsBeforeEnd(withInst, blk.modelBlock));
          onClose();
        })
        .catch(function () {
          var blk = buildInsertBlock(netlist, row);
          var withInst = insertSingleLineAtLine(netlist, Math.max(0, insertAtLine1Based - 1), blk.instanceLine);
          setNet(appendModelsBeforeEnd(withInst, blk.modelBlock));
          onClose();
        })
        .finally(function () {
          setPickBusy(false);
        });
    },
    [apiBase, netlist, insertAtLine1Based, pickDisplay, pickSel, setNet, onClose],
  );

  var requestClose = useCallback(
    function () {
      setClosing(true);
      setTimeout(function () {
        setClosing(false);
        onClose();
      }, 130);
    },
    [onClose],
  );

  useEffect(
    function () {
      if (!visible) return;
      function onDocKey(e) {
        if (e.key === "Escape") {
          e.preventDefault();
          e.stopPropagation();
          requestClose();
        }
        if (e.ctrlKey && (e.key === "l" || e.key === "L")) {
          e.preventDefault();
          e.stopPropagation();
          onClose();
        }
      }
      document.addEventListener("keydown", onDocKey, true);
      return function () {
        document.removeEventListener("keydown", onDocKey, true);
      };
    },
    [visible, requestClose, onClose],
  );

  var pickPreviewRow = pickDisplay[pickSel];
  var pickPreviewText = "";
  if (pickPreviewRow) {
    var g = generateSpiceForPart(netlist, pickPreviewRow);
    pickPreviewText = g.instanceLine + (g.modelBlock ? "\n" + g.modelBlock : "");
  }

  var totalCount =
    libCache && libCache.total != null
      ? libCache.total
      : libCache && libCache.flatIndex
        ? libCache.flatIndex.length
        : 0;

  function toggleExpanded(bucketKey) {
    setExpanded(function (ex) {
      var n = Object.assign({}, ex);
      n[bucketKey] = !n[bucketKey];
      return n;
    });
  }

  function onSearchKeyDown(e) {
    if (e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      if (resultsListRef.current) resultsListRef.current.focus();
      return;
    }
    if (e.key === "ArrowDown" && pickDisplay.length) {
      e.preventDefault();
      if (resultsListRef.current) {
        resultsListRef.current.focus();
        setPickSel(0);
      }
    }
  }

  function onResultsKeyDown(e) {
    if (e.key === "Tab" && e.shiftKey) {
      e.preventDefault();
      if (pickSearchRef.current) pickSearchRef.current.focus();
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setPickSel(function (i) {
        return Math.min(i + 1, Math.max(pickDisplay.length - 1, 0));
      });
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setPickSel(function (i) {
        if (i <= 0 && pickSearchRef.current) {
          pickSearchRef.current.focus();
          return 0;
        }
        return Math.max(i - 1, 0);
      });
      return;
    }
    if (e.key === "Enter") {
      if (pickDisplay.length) {
        e.preventDefault();
        insertSelection();
      }
      return;
    }
    if (e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      if (insertBtnRef.current) insertBtnRef.current.focus();
    }
  }

  if (!visible) return null;

  var animStyle = closing
    ? { animation: "browserFadeOut 0.13s ease-in forwards" }
    : { animation: "browserFadeIn 0.15s ease-out" };

  return (
    <div
      className="vb-browser-pop"
      style={Object.assign(
        {
          position: "absolute",
          left: Math.min(position.x, typeof window !== "undefined" ? window.innerWidth - 550 : 520),
          top: Math.min(position.y, typeof window !== "undefined" ? window.innerHeight - 400 : 300),
          width: 530,
          height: 380,
          maxHeight: 380,
          background: "#FFFFFF",
          border: "1px solid #A0A0A0",
          borderRadius: 6,
          boxShadow: "0 8px 32px rgba(0,0,0,0.18)",
          zIndex: 125,
          display: "flex",
          flexDirection: "column",
          fontFamily: "'Segoe UI',sans-serif",
          fontSize: 12,
          overflow: "hidden",
        },
        animStyle,
      )}
      onMouseDown={function (e) {
        e.stopPropagation();
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "6px 10px",
          background: "#F5F5F5",
          borderBottom: "1px solid #E0E0E0",
          flexShrink: 0,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 11, color: "#37474F", letterSpacing: "0.03em" }}>COMPONENT LIBRARY</span>
        <span style={{ marginLeft: 8, fontSize: 9, color: "#90A4AE" }}>Ctrl+L</span>
        <button
          type="button"
          aria-label="Close"
          onClick={requestClose}
          style={{
            marginLeft: "auto",
            border: "none",
            background: "transparent",
            cursor: "pointer",
            fontSize: 16,
            lineHeight: 1,
            color: "#78909C",
            padding: "0 4px",
          }}
        >
          {"\u2715"}
        </button>
      </div>
      <div style={{ padding: "6px 10px", borderBottom: "1px solid #E0E0E0", flexShrink: 0 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            ref={pickSearchRef}
            tabIndex={1}
            value={pickQ}
            onChange={function (e) {
              setPickQ(e.target.value);
            }}
            onFocus={function () {
              setSearchFocused(true);
            }}
            onBlur={function () {
              setSearchFocused(false);
            }}
            onKeyDown={function (e) {
              if (e.key === "Enter") {
                e.preventDefault();
                return;
              }
              onSearchKeyDown(e);
            }}
            placeholder="Search parts..."
            className="vb-browser-search"
            style={{
              flex: 1,
              fontSize: 12,
              padding: "6px 10px",
              border: searchFocused ? "1px solid #1565C0" : "1px solid #B0BEC5",
              borderRadius: 3,
              outline: "none",
              boxShadow: searchFocused ? "0 0 0 2px rgba(21,101,192,0.2)" : "none",
            }}
          />
          <select
            tabIndex={10}
            value={pickMfr}
            onChange={function (e) {
              setPickMfr(e.target.value);
            }}
            style={{ fontSize: 11, maxWidth: 100 }}
          >
            {pickMfrList.map(function (m, i) {
              return (
                <option key={i} value={m}>
                  {m}
                </option>
              );
            })}
          </select>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "row", flex: 1, minHeight: 0 }}>
        <div
          style={{
            width: 138,
            overflowY: "auto",
            background: "#F5F5F5",
            borderRight: "1px solid #E0E0E0",
            flexShrink: 0,
          }}
        >
          <div style={{ padding: 6, fontSize: 10, fontWeight: 700, color: "#455A64" }}>Categories</div>
          <div
            role="button"
            tabIndex={0}
            onClick={function () {
              setTreeSel({ all: true, bucket: null, sub: null, singleType: null });
            }}
            onKeyDown={function (e) {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setTreeSel({ all: true, bucket: null, sub: null, singleType: null });
              }
            }}
            style={{
              padding: "5px 8px",
              cursor: "pointer",
              fontSize: 10,
              background: treeSel.all ? "#D6E4F0" : "transparent",
              fontWeight: treeSel.all ? 700 : 400,
              borderBottom: "1px solid #ECEFF1",
            }}
          >
            All <span style={{ color: "#78909C" }}>({totalCount})</span>
          </div>
          {treeParents.map(function (node) {
            var isOne = String(node.bucket).indexOf("_ONE_") === 0;
            var act =
              !treeSel.all &&
              (isOne
                ? treeSel.singleType === node.singleType
                : treeSel.bucket === node.bucket && !treeSel.sub);
            var hasSubs = node.subs && node.subs.length > 0;
            var ex = !!expanded[node.bucket];
            return (
              <div key={node.bucket}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "2px 0",
                    fontSize: 10,
                  }}
                >
                  {hasSubs ? (
                    <button
                      type="button"
                      tabIndex={-1}
                      onClick={function (e) {
                        e.stopPropagation();
                        toggleExpanded(node.bucket);
                      }}
                      style={{
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        width: 18,
                        fontSize: 9,
                        color: "#78909C",
                        padding: 0,
                      }}
                    >
                      {ex ? "\u25BC" : "\u25B6"}
                    </button>
                  ) : (
                    <span style={{ width: 18, display: "inline-block" }} />
                  )}
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={function () {
                      if (isOne) setTreeSel({ all: false, bucket: node.bucket, sub: null, singleType: node.singleType });
                      else setTreeSel({ all: false, bucket: node.bucket, sub: null, singleType: null });
                      if (hasSubs && !ex) toggleExpanded(node.bucket);
                    }}
                    style={{
                      flex: 1,
                      padding: "4px 4px 4px 0",
                      cursor: "pointer",
                      background: act ? "#D6E4F0" : "transparent",
                      fontWeight: act ? 700 : 400,
                    }}
                  >
                    {node.label} <span style={{ color: "#78909C" }}>({node.count})</span>
                  </div>
                </div>
                {hasSubs &&
                  ex &&
                  node.subs.map(function (sub) {
                    var subAct =
                      !treeSel.all && treeSel.bucket === node.bucket && treeSel.sub === sub.key;
                    return (
                      <div
                        key={sub.key}
                        role="button"
                        tabIndex={0}
                        onClick={function () {
                          setTreeSel({ all: false, bucket: node.bucket, sub: sub.key, singleType: null });
                        }}
                        style={{
                          padding: "3px 8px 3px 22px",
                          cursor: "pointer",
                          fontSize: 10,
                          background: subAct ? "#D6E4F0" : "transparent",
                          fontWeight: subAct ? 700 : 400,
                        }}
                      >
                        {sub.label}
                      </div>
                    );
                  })}
              </div>
            );
          })}
          {(!libCache || !libCache.ready) && (
            <div style={{ padding: 8, fontSize: 10, color: "#78909C" }}>Remote mode...</div>
          )}
        </div>
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div
            style={{
              padding: "4px 8px",
              fontSize: 10,
              color: "#607D8B",
              borderBottom: "1px solid #EEE",
              flexShrink: 0,
            }}
          >
            Results <span style={{ fontWeight: 700 }}>{pickDisplay.length}</span>
          </div>
          <div
            ref={resultsListRef}
            tabIndex={2}
            role="listbox"
            aria-label="Part results"
            onKeyDown={onResultsKeyDown}
            style={{ flex: 1, overflowY: "auto", minHeight: 60, outline: "none" }}
          >
            {pickBusy && pickDisplay.length === 0 && (
              <div style={{ padding: 10, color: "#90A4AE", fontSize: 11 }}>Searching...</div>
            )}
            {pickDisplay.map(function (row, i) {
              return (
                <div
                  key={row.part_number + "-" + i}
                  role="option"
                  aria-selected={i === pickSel}
                  tabIndex={-1}
                  onClick={function () {
                    setPickSel(i);
                  }}
                  style={{
                    padding: "5px 8px",
                    cursor: "pointer",
                    background: i === pickSel ? "#D6E4F0" : "#FFF",
                    borderBottom: "1px solid #F5F5F5",
                    fontSize: 11,
                  }}
                >
                  <span style={{ fontWeight: 700, color: "#1565C0" }}>{row.part_number}</span>{" "}
                  <span style={{ color: "#78909C" }}>{row.comp_type}</span>
                  <div
                    style={{
                      color: "#9E9E9E",
                      fontSize: 10,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {formatPartBrief(row)}
                  </div>
                </div>
              );
            })}
            {!pickBusy && pickDisplay.length === 0 && (
              <div style={{ padding: 10, color: "#B0BEC5", fontSize: 11 }}>No parts</div>
            )}
          </div>
        </div>
      </div>
      <div
        style={{
          borderTop: "1px solid #E0E0E0",
          padding: 8,
          background: "#F8F8F8",
          flexShrink: 0,
        }}
      >
        <div style={{ fontSize: 9, color: "#78909C", marginBottom: 4, fontWeight: 600 }}>Preview</div>
        <pre
          style={{
            margin: 0,
            fontSize: 10,
            fontFamily: "'Courier New',monospace",
            color: "#37474F",
            whiteSpace: "pre-wrap",
            maxHeight: 72,
            overflow: "auto",
            background: "#F8F8F8",
            padding: 6,
            borderRadius: 3,
            border: "1px solid #ECEFF1",
          }}
        >
          {pickPreviewText || "Select a part"}
        </pre>
        <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
          <button
            ref={insertBtnRef}
            type="button"
            tabIndex={3}
            onKeyDown={function (e) {
              if (e.key === "Tab" && e.shiftKey && resultsListRef.current) {
                e.preventDefault();
                resultsListRef.current.focus();
              }
            }}
            onClick={insertSelection}
            disabled={pickBusy || !pickDisplay.length}
            style={{
              fontSize: 11,
              padding: "4px 14px",
              borderRadius: 3,
              border: "1px solid #2E7D32",
              background: "#2E7D32",
              color: "#FFF",
              cursor: pickBusy ? "wait" : "pointer",
              fontWeight: 600,
            }}
          >
            Insert at Cursor
          </button>
          <button
            type="button"
            tabIndex={5}
            onClick={function () {
              var r = pickPreviewRow;
              if (r && r.datasheet_url) window.open(r.datasheet_url, "_blank");
            }}
            disabled={!pickPreviewRow || !pickPreviewRow.datasheet_url}
            style={{
              fontSize: 11,
              padding: "4px 10px",
              borderRadius: 3,
              border: "1px solid #B0BEC5",
              background: "#FFF",
              cursor: "pointer",
            }}
          >
            Datasheet
          </button>
          <button
            type="button"
            tabIndex={6}
            onClick={requestClose}
            style={{
              fontSize: 11,
              padding: "4px 10px",
              borderRadius: 3,
              border: "1px solid #B0BEC5",
              background: "#FFF",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
