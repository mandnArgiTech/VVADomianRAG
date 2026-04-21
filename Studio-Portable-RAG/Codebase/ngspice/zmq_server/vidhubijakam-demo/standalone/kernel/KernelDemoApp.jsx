import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from "react";
import { initLibraryCache } from "../libraryCache.js";
import {
  defaultApiBaseForDemo,
  defaultDeepSeekKeyFromEnv,
  normalizeApiBase,
  fetchOnce503Retry,
} from "./apiConfig.js";
import { inferAnalysisFromNetlistLower, firstLoadableCatalogItem } from "./netlistInference.js";
import { FALLBACK } from "./fallbackCatalog.js";
import { VB_HL_CSS } from "./spiceHighlight.js";
import KernelNetlistEditor from "./KernelNetlistEditor.jsx";
import FileMenuBar from "./FileMenuBar.jsx";
import ResizablePanel, { readStoredPanelSize } from "./layout/ResizablePanel.jsx";
import ToolWindowBar from "./layout/ToolWindowBar.jsx";
import BottomPanel from "./layout/BottomPanel.jsx";
import TopToolbar from "./layout/TopToolbar.jsx";
import EditorTabBar from "./tabs/EditorTabBar.jsx";
import { createTabsState, tabsReducer, getActiveTab } from "./tabs/EditorTabState.js";
import OutputConsole from "./console/OutputConsole.jsx";
import DsoSimulationTab from "./DsoSimulationTab.jsx";
import DcOpSimulationTab from "./DcOpSimulationTab.jsx";
import SchematicCanvas from "./canvas/SchematicCanvas.jsx";
import { readUserCircuits, upsertUserCircuit } from "./userCircuitsStorage.js";

var API_DEF = defaultApiBaseForDemo();

/** One-line summary for Output tab from bridge ``diag_events`` JSON. */
function formatDiagEvent(ev) {
  if (!ev || !ev.hook) return null;
  function ex(x) {
    if (x == null || typeof x !== "number" || !isFinite(x)) return "?";
    return x.toExponential(2);
  }
  function num(x, def) {
    if (x == null || typeof x !== "number" || !isFinite(x)) return def;
    return x;
  }
  switch (ev.hook) {
    case "nr_iter":
      return (
        "NR iter " +
        ev.iter +
        ": max_dx=" +
        ex(ev.max_dx) +
        " max_rhs=" +
        ex(ev.max_rhs) +
        " noncon=" +
        (ev.noncon != null ? ev.noncon : "?") +
        (ev.converged ? " CONV" : "")
      );
    case "limiter":
      return (
        "Limiter " +
        (ev.fn || "") +
        (ev.inst ? " " + ev.inst : "") +
        ": " +
        num(ev.vnew_raw, 0).toFixed(4) +
        "V → " +
        num(ev.vnew_lim, 0).toFixed(4) +
        "V"
      );
    case "gmin":
      return (
        "GMIN step: " +
        ex(ev.val) +
        (ev.converged ? " (conv in " + (ev.iters != null ? ev.iters : "?") + " iters)" : " (no conv)")
      );
    case "src_step":
      return (
        "Source step: factor=" +
        num(ev.factor, 0).toFixed(4) +
        (ev.converged ? " conv" : "") +
        " iters=" +
        (ev.iters != null ? ev.iters : "?")
      );
    case "device": {
      var vals = ev.values || {};
      var parts = Object.keys(vals).map(function (k) {
        return k + "=" + ex(vals[k]);
      });
      return "Device " + (ev.type || "?") + " " + (ev.inst || "") + ": " + parts.join(" ");
    }
    case "matrix":
      return (
        "Matrix cond=" +
        ex(ev.ratio) +
        " size=" +
        (ev.size != null ? ev.size : "?") +
        " min_piv=" +
        ex(ev.min_piv)
      );
    default:
      return null;
  }
}

export default function KernelDemoApp() {
  var firstFb = FALLBACK[0];
  var _tabs = useReducer(tabsReducer, undefined, function () {
    return createTabsState(firstFb.net, firstFb.a, {
      label: firstFb.t,
      selP: firstFb.p || "fb_0",
    });
  });
  var tabsState = _tabs[0];
  var tabsDispatch = _tabs[1];

  var tabsRef = useRef(tabsState);
  tabsRef.current = tabsState;

  var _r = useState(null),
    res = _r[0],
    setRes = _r[1];
  var _e = useState(null),
    err = _e[0],
    setErr = _e[1];
  var _d = useState(null),
    drc = _d[0],
    setDrc = _d[1];
  var _b = useState(false),
    busy = _b[0],
    setBusy = _b[1];
  var _ba = useState(normalizeApiBase(API_DEF)),
    base = _ba[0],
    setBase = _ba[1];
  var _cf = useState(false),
    cfg = _cf[0],
    setCfg = _cf[1];
  var _sn = useState(0),
    simN = _sn[0],
    setSimN = _sn[1];
  var _q = useState(""),
    search = _q[0],
    setSearch = _q[1];
  var _cat = useState(
    FALLBACK.map(function (f, i) {
      return Object.assign({}, f, { p: "fb_" + i });
    }),
  ),
    catalog = _cat[0],
    setCatalog = _cat[1];
  var _col = useState({}),
    collapsed = _col[0],
    setCollapsed = _col[1];
  var _ucRev = useState(0),
    userCircRev = _ucRev[0],
    bumpUserCirc = _ucRev[1];
  var _kb = useState("loading"),
    kernelBoot = _kb[0],
    setKernelBoot = _kb[1];
  var _kst = useState(""),
    kernelStep = _kst[0],
    setKernelStep = _kst[1];
  var _lc = useState(null),
    libCache = _lc[0],
    setLibCache = _lc[1];
  var _ls = useState("idle"),
    libStatus = _ls[0],
    setLibStatus = _ls[1];
  var _lm = useState(""),
    libMsg = _lm[0],
    setLibMsg = _lm[1];
  var _aiKey = useState(defaultDeepSeekKeyFromEnv),
    aiKey = _aiKey[0],
    setAiKey = _aiKey[1];
  var _aiShowKey = useState(false),
    aiShowKey = _aiShowKey[0],
    setAiShowKey = _aiShowKey[1];

  var consoleLogRef = useRef([]);
  var fileInputRef = useRef(null);
  var netEditorRef = useRef(null);
  var _logV = useState(0);
  var logVersion = _logV[0];
  var bumpLogVersion = _logV[1];

  var logEntries = useMemo(
    function () {
      return consoleLogRef.current.slice();
    },
    [logVersion],
  );

  var appendLog = useCallback(function (level, text) {
    var row = { ts: Date.now(), level: level, text: String(text || "") };
    consoleLogRef.current = consoleLogRef.current.concat([row]);
    if (consoleLogRef.current.length > 500) consoleLogRef.current = consoleLogRef.current.slice(-500);
    bumpLogVersion(function (v) {
      return v + 1;
    });
  }, []);

  var _lw = useState(function () {
    return readStoredPanelSize("vb-left-pane-w", 220, 150, 400);
  });
  var leftW = _lw[0];
  var setLeftW = _lw[1];
  var _bh = useState(function () {
    return readStoredPanelSize("vb-bottom-pane-h", 200, 120, 600);
  });
  var bottomH = _bh[0];
  var setBottomH = _bh[1];
  var _lo = useState(true);
  var leftOpen = _lo[0];
  var setLeftOpen = _lo[1];
  var _bo = useState(true);
  var bottomOpen = _bo[0];
  var setBottomOpen = _bo[1];
  var _abt = useState("output");
  var activeBottomTab = _abt[0];
  var setActiveBottomTab = _abt[1];

  var abtR = useRef(null);
  var libInitIdRef = useRef(0);

  var activeTab = getActiveTab(tabsState) || tabsState.tabs[0];
  var net = activeTab.net;
  var an = activeTab.an;
  var selP = activeTab.selP;

  useEffect(
    function () {
      var root = normalizeApiBase(base);
      var cancelled = false;
      setKernelBoot("loading");
      setKernelStep("");
      function poll() {
        if (cancelled) return;
        fetchOnce503Retry((root || "") + "/api/boot/status")
          .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json();
          })
          .then(function (d) {
            if (cancelled) return;
            setKernelStep(String((d && (d.current_step != null ? d.current_step : d.currentStep)) || ""));
            setKernelBoot(d && d.ready ? "ready" : "starting");
          })
          .catch(function () {
            if (!cancelled) setKernelBoot("offline");
          });
      }
      poll();
      var id = setInterval(poll, 3000);
      return function () {
        cancelled = true;
        clearInterval(id);
      };
    },
    [base],
  );

  useEffect(
    function () {
      var root = normalizeApiBase(base);
      function applyFallback() {
        var fb = FALLBACK.map(function (f, i) {
          return Object.assign({}, f, { p: "fb_" + i });
        });
        setCatalog(fb);
        tabsDispatch({
          type: "SYNC_CATALOG_TO_ACTIVE",
          payload: {
            net: FALLBACK[0].net,
            an: FALLBACK[0].a,
            selP: fb[0].p || fb[0].t,
            label: FALLBACK[0].t,
          },
        });
      }
      function mapIndexToCatalog(data) {
        var items = [];
        (data.categories || []).forEach(function (cat) {
          (cat.circuits || []).forEach(function (cir) {
            var rel = String(cir.file || cir.path || "").trim();
            var nl = String(cir.netlist || "");
            var cl = nl.toLowerCase();
            var rawAt = String(cir.analysis || "").trim().toLowerCase();
            var at = /^(op|ac|tran|dc)$/.test(rawAt) ? rawAt : inferAnalysisFromNetlistLower(cl);
            items.push({ t: cir.name || "?", c: cat.name || "misc", a: at, p: rel, net: nl });
          });
        });
        return items;
      }
      fetchOnce503Retry((root || "") + "/api/examples/index")
        .then(function (r) {
          if (!r.ok) throw new Error("examples index HTTP " + r.status);
          return r.json();
        })
        .then(function (data) {
          var items = mapIndexToCatalog(data);
          if (!items.length) throw new Error("examples index empty");
          var first = firstLoadableCatalogItem(items);
          if (!first) throw new Error("no loadable examples in index");
          setErr(null);
          setCatalog(items);
          if (first.net && String(first.net).trim()) {
            tabsDispatch({
              type: "SYNC_CATALOG_TO_ACTIVE",
              payload: {
                net: first.net,
                an: first.a || "op",
                selP: first.p || first.t,
                label: first.t,
              },
            });
            return;
          }
          if (first.p) {
            var cUrl = (root || "") + "/api/examples/circuit?path=" + encodeURIComponent(first.p);
            return fetchOnce503Retry(cUrl)
              .then(function (r2) {
                if (!r2.ok) throw new Error("examples circuit HTTP " + r2.status);
                return r2.json();
              })
              .then(function (d) {
                var txt = d.text || "";
                var cl = txt.toLowerCase();
                var inferred = inferAnalysisFromNetlistLower(cl);
                var useAn = inferred !== "op" ? inferred : first.a || "op";
                tabsDispatch({
                  type: "TAB_LOAD_FROM_CATALOG",
                  payload: {
                    net: txt,
                    an: useAn,
                    label: first.t,
                    selP: first.p,
                  },
                });
              })
              .catch(function (e) {
                setErr(String(e.message || e));
              });
          }
          throw new Error("first loadable item has no file and no netlist");
        })
        .catch(function () {
          setErr(null);
          applyFallback();
        });
    },
    [base],
  );

  useEffect(
    function () {
      var myId = ++libInitIdRef.current;
      setLibStatus("loading");
      setLibMsg("Indexing library...");
      initLibraryCache(normalizeApiBase(base)).then(function (cache) {
        if (libInitIdRef.current !== myId) return;
        setLibCache(cache);
        if (cache.error) {
          setLibStatus("offline");
          setLibMsg("Library offline");
        } else if (cache.ready && (!cache.types || cache.types.length === 0)) {
          setLibStatus("empty");
          setLibMsg("Library empty");
        } else if (cache.ready) {
          setLibStatus("ready");
          var n = cache.flatIndex.length,
            ty = cache.types.length;
          setLibMsg(n + " parts cached across " + ty + " types");
          setTimeout(function () {
            if (libInitIdRef.current === myId) setLibMsg("");
          }, 3500);
        } else {
          setLibStatus("empty");
          setLibMsg("Library empty");
        }
      });
    },
    [base],
  );

  var grouped = useMemo(
    function () {
      var g = {};
      catalog.forEach(function (i) {
        var c = i.c || "misc";
        if (!g[c]) g[c] = [];
        g[c].push(i);
      });
      return g;
    },
    [catalog],
  );
  var filtered = useMemo(
    function () {
      if (!search) return grouped;
      var q = search.toLowerCase();
      var g = {};
      Object.keys(grouped).forEach(function (c) {
        var it = grouped[c].filter(function (i) {
          return i.t.toLowerCase().indexOf(q) >= 0 || c.toLowerCase().indexOf(q) >= 0;
        });
        if (it.length) g[c] = it;
      });
      return g;
    },
    [grouped, search],
  );

  var userCircuitsList = useMemo(
    function () {
      return readUserCircuits();
    },
    [userCircRev],
  );

  /** Catalog groups plus persistent **User** folder (localStorage). */
  var explorerGroups = useMemo(
    function () {
      var q = search.toLowerCase().trim();
      var userItems = userCircuitsList.map(function (e) {
        var an = String(e.an || "op")
          .trim()
          .toLowerCase();
        if (!/^(op|ac|tran|dc)$/.test(an)) an = "op";
        return { t: e.name, p: "user:" + e.id, c: "User", a: an, net: e.net };
      });
      if (q) {
        userItems = userItems.filter(function (i) {
          return i.t.toLowerCase().indexOf(q) >= 0;
        });
      }
      var g = Object.assign({}, filtered);
      g.User = userItems;
      return g;
    },
    [filtered, userCircuitsList, search],
  );

  var loadC = useCallback(
    function (item) {
      setRes(null);
      setErr(null);
      setDrc(null);
      var r0 = normalizeApiBase(base);
      function normAn(a, txt) {
        var raw = String(a || "")
          .trim()
          .toLowerCase();
        if (/^(op|ac|tran|dc)$/.test(raw)) return raw;
        return inferAnalysisFromNetlistLower(String(txt || "").toLowerCase());
      }
      if (item.net && String(item.net).trim()) {
        tabsDispatch({
          type: "OPEN_TAB_WITH_CIRCUIT",
          payload: {
            net: item.net,
            an: normAn(item.a, item.net),
            label: item.t,
            selP: item.p || item.t,
          },
        });
      } else if (item.p && String(item.p).trim()) {
        fetchOnce503Retry((r0 || "") + "/api/examples/circuit?path=" + encodeURIComponent(item.p))
          .then(function (r) {
            if (!r.ok) throw new Error("examples circuit HTTP " + r.status);
            return r.json();
          })
          .then(function (d) {
            var txt = d.text || "";
            var inf = inferAnalysisFromNetlistLower(txt.toLowerCase());
            var anUse = inf !== "op" ? inf : normAn(item.a, txt);
            tabsDispatch({
              type: "OPEN_TAB_WITH_CIRCUIT",
              payload: {
                net: txt,
                an: anUse,
                label: item.t,
                selP: item.p,
              },
            });
          })
          .catch(function (e) {
            setErr(String(e.message || e));
          });
      } else {
        setErr("This example has no circuit path or embedded netlist.");
      }
    },
    [base],
  );

  var doSim = useCallback(
    function () {
      if (abtR.current) abtR.current.abort();
      var tab = getActiveTab(tabsRef.current);
      if (!tab) return;
      var netT = tab.net;
      var anT = tab.an;
      var ctrl = new AbortController();
      abtR.current = ctrl;
      setBusy(true);
      setErr(null);
      setRes(null);
      appendLog("info", "Running simulation (" + String(anT).toUpperCase() + ")…");
      var r0 = normalizeApiBase(base);
      var simInit = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ components: [], netlist_text: netT, analysis_type: anT }),
        signal: ctrl.signal,
      };
      fetchOnce503Retry((r0 || "") + "/api/simulate", simInit)
        .then(function (r) {
          return r.json().then(function (d) {
            if (!r.ok) throw new Error(d.detail || "HTTP " + r.status);
            return d;
          });
        })
        .then(function (d) {
          if (!ctrl.signal.aborted) {
            setRes(d);
            setSimN(function (c) {
              return c + 1;
            });
            appendLog("success", "Simulation finished in " + (d && d.solve_time_ms != null ? Number(d.solve_time_ms).toFixed(1) : "?") + " ms");
            if (d && Array.isArray(d.diag_events) && d.diag_events.length > 0) {
              appendLog("info", "--- Diagnostics (" + d.diag_events.length + " events) ---");
              d.diag_events.forEach(function (ev) {
                var msg = formatDiagEvent(ev);
                if (msg) appendLog("diag", msg);
              });
            }
          }
        })
        .catch(function (e) {
          if (e.name !== "AbortError") {
            setErr(e.message);
            appendLog("error", "Simulation failed: " + (e.message || String(e)));
          }
        })
        .finally(function () {
          setBusy(false);
        });
    },
    [base, appendLog],
  );

  var doDRC = useCallback(
    function () {
      setDrc(null);
      var tab = getActiveTab(tabsRef.current);
      if (!tab) return;
      var netT = tab.net;
      appendLog("info", "Running DRC…");
      var r0 = normalizeApiBase(base);
      var drcInit = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: netT }),
      };
      fetchOnce503Retry((r0 || "") + "/api/parse-netlist", drcInit)
        .then(function (r) {
          return r.json().then(function (d) {
            if (!r.ok) throw new Error(d.detail || "HTTP " + r.status);
            setDrc({ ok: true, d: d });
            var nc = d && d.components ? d.components.length : 0;
            var nm = d && d.models ? Object.keys(d.models).length : 0;
            appendLog("success", "DRC OK — " + nc + " components, " + nm + " models");
          });
        })
        .catch(function (e) {
          setDrc({ ok: false, m: e.message });
          appendLog("error", "DRC failed: " + (e.message || String(e)));
        });
    },
    [base, appendLog],
  );

  var setNetFromEditor = useCallback(function (next) {
    tabsDispatch({ type: "UPDATE_NET", payload: { net: next } });
  }, []);

  var doUndo = useCallback(function () {
    tabsDispatch({ type: "UNDO_NET" });
  }, []);

  var doRedo = useCallback(function () {
    tabsDispatch({ type: "REDO_NET" });
  }, []);

  var onLoadCircuitClick = useCallback(function () {
    if (fileInputRef.current) fileInputRef.current.click();
  }, []);

  var onSaveCircuit = useCallback(function () {
    var tab = getActiveTab(tabsRef.current);
    if (!tab) return;
    var entry = upsertUserCircuit(tab.label, tab.net, tab.an);
    tabsDispatch({
      type: "MARK_ACTIVE_SAVED",
      payload: { selP: "user:" + entry.id, label: entry.name },
    });
    bumpUserCirc(function (v) {
      return v + 1;
    });
    appendLog("info", 'Saved to Circuit Explorer → User as "' + entry.name + '"');
  }, [appendLog]);

  var onFileChosen = useCallback(
    function (e) {
      var f = e.target.files && e.target.files[0];
      e.target.value = "";
      if (!f) return;
      var reader = new FileReader();
      reader.onload = function () {
        var txt = String(reader.result || "");
        var anUse = inferAnalysisFromNetlistLower(txt.toLowerCase());
        tabsDispatch({
          type: "OPEN_TAB_WITH_CIRCUIT",
          payload: {
            net: txt,
            an: anUse,
            label: String(f.name || "Circuit").replace(/\.[^.\\/]+$/i, "") || "Circuit",
            selP: "file:" + f.name,
          },
        });
        setRes(null);
        setErr(null);
        appendLog("info", "Loaded " + f.name);
      };
      reader.readAsText(f);
    },
    [appendLog],
  );

  var onExitApp = useCallback(function () {
    try {
      window.close();
    } catch {
      /* */
    }
    setTimeout(function () {
      window.alert("Close this browser tab to exit the demo.");
    }, 100);
  }, []);

  useEffect(
    function () {
      function onDocKey(ev) {
        var t = ev.target;
        if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
          if (t.getAttribute("type") === "password" || t.getAttribute("type") === "file") return;
          if (t.closest && t.closest('[style*="FFF8E1"]')) return;
          if (t.closest && t.closest('[style*="E3F2FD"]') && t.placeholder && String(t.placeholder).indexOf("DeepSeek") >= 0)
            return;
        }
        var mod = ev.ctrlKey || ev.metaKey;
        if (mod && (ev.key === "o" || ev.key === "O")) {
          ev.preventDefault();
          if (fileInputRef.current) fileInputRef.current.click();
        }
        if (mod && (ev.key === "s" || ev.key === "S")) {
          ev.preventDefault();
          onSaveCircuit();
        }
      }
      document.addEventListener("keydown", onDocKey, true);
      return function () {
        document.removeEventListener("keydown", onDocKey, true);
      };
    },
    [onSaveCircuit],
  );

  var setAnToolbar = useCallback(function (v) {
    tabsDispatch({ type: "SET_AN", payload: { an: v } });
  }, []);

  var lc = net.split("\n").length;
  var canUndo = (activeTab.undoStack || []).length > 0;
  var canRedo = (activeTab.redoStack || []).length > 0;
  var anCol = { op: "#2E7D32", ac: "#1565C0", tran: "#E65100", dc: "#7B1FA2" };
  var libBar = "Library: ...";
  if (libStatus === "loading") libBar = "Library: loading...";
  else if (libStatus === "offline") libBar = "Library: offline";
  else if (libStatus === "empty") libBar = "Library: empty";
  else if (libStatus === "ready" && libCache)
    libBar = "Library: " + (libCache.total || libCache.flatIndex.length) + " parts - " + (libCache.types || []).length + " types";

  var explorerBody = (
    <>
      <div style={{ padding: "6px 8px", borderBottom: "1px solid #E0E0E0", background: "#F5F5F5" }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: "#555", marginBottom: 3 }}>Circuit Explorer</div>
        <input
          value={search}
          onChange={function (e) {
            setSearch(e.target.value);
          }}
          placeholder="Search..."
          style={{
            width: "100%",
            fontSize: 12,
            padding: "3px 6px",
            borderRadius: 3,
            border: "1px solid #C0C0C0",
            background: "#FFF",
            outline: "none",
          }}
        />
      </div>
      <div style={{ flex: 1, overflowY: "auto" }}>
        {Object.keys(explorerGroups)
          .sort(function (a, b) {
            if (a === "User") return -1;
            if (b === "User") return 1;
            return a.localeCompare(b);
          })
          .map(function (cat) {
            var items = explorerGroups[cat];
            var isC = collapsed[cat];
            return (
              <div key={cat}>
                <div
                  onClick={function () {
                    var n2 = {};
                    for (var k in collapsed) n2[k] = collapsed[k];
                    n2[cat] = !isC;
                    setCollapsed(n2);
                  }}
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: "#555",
                    padding: "5px 8px",
                    background: "#F0F0F0",
                    borderBottom: "1px solid #E8E8E8",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    userSelect: "none",
                  }}
                >
                  <span>
                    {isC ? "\u25B6" : "\u25BC"} {cat}
                  </span>
                  <span style={{ fontSize: 10, color: "#AAA" }}>{items.length}</span>
                </div>
                {!isC && cat === "User" && items.length === 0 && (
                  <div
                    style={{
                      padding: "6px 12px 8px 16px",
                      fontSize: 11,
                      color: "#888",
                      fontStyle: "italic",
                    }}
                  >
                    No saved circuits yet. Use File → Save or Ctrl+S to store the active tab here (browser
                    localStorage).
                  </div>
                )}
                {!isC &&
                  items.map(function (item, i) {
                    var act = (item.p || item.t) === selP;
                    var ab = item.a || "op";
                    return (
                      <div
                        key={cat + ":" + i + ":" + (item.p || item.t)}
                        onClick={function () {
                          loadC(item);
                        }}
                        style={{
                          padding: "3px 8px 3px 16px",
                          fontSize: 11.5,
                          cursor: "pointer",
                          background: act ? "#D6E4F0" : "transparent",
                          color: act ? "#1565C0" : "#444",
                          borderLeft: act ? "3px solid #1565C0" : "3px solid transparent",
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                          overflow: "hidden",
                          whiteSpace: "nowrap",
                        }}
                      >
                        <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>{item.t}</span>
                        <span
                          style={{
                            fontSize: 8,
                            padding: "1px 4px",
                            borderRadius: 2,
                            background: anCol[ab] || "#888",
                            color: "#FFF",
                            fontWeight: 700,
                          }}
                        >
                          {String(ab).toUpperCase()}
                        </span>
                      </div>
                    );
                  })}
              </div>
            );
          })}
      </div>
    </>
  );

  var bottomTabs = useMemo(
    function () {
      return [
        {
          id: "output",
          label: "Output",
          content: (
            <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, minWidth: 0, height: "100%" }}>
              <OutputConsole entries={logEntries} />
            </div>
          ),
        },
        { id: "dcop", label: "DC OP", content: <DcOpSimulationTab r={res} /> },
        { id: "dso", label: "DSO", content: <DsoSimulationTab r={res} /> },
        { id: "schematic", label: "Schematic", content: <SchematicCanvas net={net} /> },
      ];
    },
    [logEntries, res, net],
  );

  var leftBarItems = useMemo(
    function () {
      return [{ id: "explorer", label: "Explorer", icon: "\u25A4", active: leftOpen }];
    },
    [leftOpen],
  );

  var bottomBarItems = useMemo(
    function () {
      return [{ id: "tools", label: "Bottom", icon: "\u25A4", active: bottomOpen }];
    },
    [bottomOpen],
  );

  return (
    <div
      style={{
        fontFamily: "'Segoe UI','Helvetica Neue',Arial,sans-serif",
        background: "#F2F2F2",
        color: "#333",
        height: "100vh",
        fontSize: 13,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: VB_HL_CSS }} />
      <input
        ref={fileInputRef}
        type="file"
        accept=".cir,.net,.sp,.txt,.cct"
        style={{ display: "none" }}
        onChange={onFileChosen}
      />
      <FileMenuBar
        onLoadCircuit={onLoadCircuitClick}
        onSaveCircuit={onSaveCircuit}
        onCut={function () {
          if (netEditorRef.current) netEditorRef.current.cut();
        }}
        onCopy={function () {
          if (netEditorRef.current) netEditorRef.current.copy();
        }}
        onPaste={function () {
          if (netEditorRef.current) netEditorRef.current.paste();
        }}
        onUndo={doUndo}
        onRedo={doRedo}
        canUndo={canUndo}
        canRedo={canRedo}
        onExit={onExitApp}
      />
      <TopToolbar
        catalogCount={catalog.length}
        apiOpen={cfg}
        onToggleApi={function () {
          setCfg(!cfg);
        }}
        kernelBoot={kernelBoot}
        kernelStep={kernelStep}
        an={an}
        setAn={function (v) {
          setAnToolbar(v);
        }}
        onRun={doSim}
        onDRC={doDRC}
        busy={busy}
        aiKey={aiKey}
        onNeedAiKey={function () {
          setAiShowKey(true);
        }}
        libStatus={libStatus}
        libBar={libBar}
        libMsg={libMsg}
        simN={simN}
        lineCount={lc}
      />
      {cfg && (
        <div
          style={{
            background: "#FFF8E1",
            borderBottom: "1px solid #FFD54F",
            padding: "5px 16px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          <span style={{ fontWeight: 600, color: "#F57F17" }}>Backend:</span>
          <input
            value={base}
            onChange={function (e) {
              setBase(e.target.value);
            }}
            style={{
              fontFamily: "'Courier New',monospace",
              fontSize: 12,
              padding: "2px 6px",
              borderRadius: 3,
              border: "1px solid #D0D0D0",
              width: 280,
            }}
          />
          <button
            onClick={function () {
              setBase(normalizeApiBase(base));
              setCfg(false);
            }}
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 3,
              border: "1px solid #B0B0B0",
              background: "#FFF",
              cursor: "pointer",
            }}
          >
            OK
          </button>
        </div>
      )}
      {aiShowKey && (
        <div
          style={{
            background: "#E3F2FD",
            borderBottom: "1px solid #BBDEFB",
            padding: "5px 16px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          <span style={{ fontWeight: 600, color: "#1565C0" }}>DeepSeek API Key:</span>
          <input
            value={aiKey}
            onChange={function (e) {
              setAiKey(e.target.value);
            }}
            type="password"
            placeholder="sk-... (or set DEEP_SEEK_API_KEY in repo .env)"
            style={{
              fontFamily: "'Courier New',monospace",
              fontSize: 12,
              padding: "2px 6px",
              borderRadius: 3,
              border: "1px solid #B0B0B0",
              width: 300,
            }}
          />
          <button
            onClick={function () {
              setAiShowKey(false);
            }}
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 3,
              border: "1px solid #B0B0B0",
              background: "#FFF",
              cursor: "pointer",
            }}
          >
            {aiKey.trim() ? "Saved" : "Close"}
          </button>
          <span style={{ fontSize: 10, color: "#888" }}>
            Prefilled from repo .env (DEEP_SEEK_API_KEY) when using Vite; sent only to your /api/ai/generate endpoint
          </span>
        </div>
      )}

      <div style={{ display: "flex", flex: 1, flexDirection: "row", minHeight: 0, overflow: "hidden" }}>
        <ToolWindowBar
          direction="left"
          items={leftBarItems}
          onToggle={function (id) {
            if (id === "explorer") {
              setLeftOpen(function (v) {
                return !v;
              });
            }
          }}
        />
        {leftOpen && (
          <ResizablePanel
            direction="right"
            size={leftW}
            onResize={setLeftW}
            minSize={150}
            maxSize={400}
            storageKey="vb-left-pane-w"
          >
            <div style={{ background: "#FAFAFA", borderRight: "1px solid #D0D0D0", display: "flex", flexDirection: "column", height: "100%" }}>
              {explorerBody}
            </div>
          </ResizablePanel>
        )}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0, overflow: "hidden" }}>
          <EditorTabBar
            tabs={tabsState.tabs.map(function (t) {
              return { id: t.id, label: t.label, dirty: t.dirty };
            })}
            activeId={tabsState.activeId}
            onSelect={function (id) {
              tabsDispatch({ type: "SELECT_TAB", payload: { id: id } });
            }}
            onClose={function (id) {
              tabsDispatch({ type: "CLOSE_TAB", payload: { id: id } });
            }}
            onAdd={function () {
              tabsDispatch({ type: "ADD_TAB" });
            }}
          />
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden", padding: "10px 14px", background: "#F2F2F2" }}>
            {drc &&
              (drc.ok ? (
                <div
                  style={{
                    fontSize: 12,
                    padding: "5px 10px",
                    background: "#E8F5E9",
                    border: "1px solid #A5D6A7",
                    borderRadius: 3,
                    color: "#2E7D32",
                    marginBottom: 8,
                    flexShrink: 0,
                  }}
                >
                  DRC OK \u2014 {(drc.d && drc.d.components ? drc.d.components.length : 0)} components,{" "}
                  {Object.keys((drc.d && drc.d.models) || {}).length} models
                </div>
              ) : (
                <div
                  style={{
                    fontSize: 12,
                    padding: "5px 10px",
                    background: "#FFEBEE",
                    border: "1px solid #EF9A9A",
                    borderRadius: 3,
                    color: "#C62828",
                    marginBottom: 8,
                    whiteSpace: "pre-wrap",
                    flexShrink: 0,
                  }}
                >
                  {drc.m}
                </div>
              ))}
            <div style={{ flex: "2 1 0", minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <KernelNetlistEditor
                ref={netEditorRef}
                key={activeTab.circuitKey}
                net={net}
                setNet={setNetFromEditor}
                apiBase={base}
                doSim={doSim}
                doDRC={doDRC}
                libCache={libCache}
                circuitKey={activeTab.circuitKey}
                aiKey={aiKey}
                onNeedAiKey={function () {
                  setAiShowKey(true);
                }}
                onUndo={doUndo}
                onRedo={doRedo}
              />
            </div>
            {err && (
              <div
                style={{
                  padding: "6px 10px",
                  background: "#FFEBEE",
                  border: "1px solid #EF9A9A",
                  borderRadius: 3,
                  color: "#C62828",
                  fontSize: 12,
                  fontFamily: "'Courier New',monospace",
                  marginTop: 8,
                  whiteSpace: "pre-wrap",
                  flexShrink: 0,
                }}
              >
                {err}
              </div>
            )}
            {res && res.expansion_log && res.expansion_log.length > 0 && (
              <div
                style={{
                  fontSize: 11,
                  color: "#666",
                  fontFamily: "'Courier New',monospace",
                  padding: "4px 8px",
                  background: "#F8F8F8",
                  border: "1px solid #E0E0E0",
                  borderRadius: 3,
                  marginTop: 8,
                  maxHeight: 50,
                  overflowY: "auto",
                  flexShrink: 0,
                }}
              >
                {res.expansion_log.map(function (l, i) {
                  return <div key={i}>{l}</div>;
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {bottomOpen && (
        <ResizablePanel
          direction="top"
          size={bottomH}
          onResize={setBottomH}
          minSize={120}
          maxSize={600}
          storageKey="vb-bottom-pane-h"
        >
          <BottomPanel tabs={bottomTabs} activeTab={activeBottomTab} onTabChange={setActiveBottomTab} />
        </ResizablePanel>
      )}
      <ToolWindowBar
        direction="bottom"
        items={bottomBarItems}
        onToggle={function (id) {
          if (id === "tools") {
            setBottomOpen(function (v) {
              return !v;
            });
          }
        }}
      />

      <style>{`@keyframes sp{to{transform:rotate(360deg)}}@keyframes aiSlideIn{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}@keyframes browserFadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}@keyframes browserFadeOut{from{opacity:1;transform:translateY(0)}to{opacity:0;transform:translateY(-4px)}}`}</style>
    </div>
  );
}
