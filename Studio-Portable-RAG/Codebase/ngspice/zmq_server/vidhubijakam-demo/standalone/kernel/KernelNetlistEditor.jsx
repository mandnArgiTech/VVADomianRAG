import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
  useDeferredValue,
  forwardRef,
  useImperativeHandle,
} from "react";
import { searchLocal, searchRemote, getTypes } from "../libraryCache.js";
import { buildInlineAIPrompt, validateAIResponse, getResolvedCatalogTypesForQuery } from "../aiLibraryContext.js";
import { buildInsertBlock, replaceWordAtCursor, appendModelsBeforeEnd } from "../spiceInsert.js";
import { normalizeApiBase, fetchOnce503Retry } from "./apiConfig.js";
import { esc, hlS } from "./spiceHighlight.js";
import { kindBg } from "./spiceAutocompleteData.js";
import {
  NET_GUTTER_PX,
  NET_ED_FONT,
  NET_ED_FONT_SIZE,
  NET_ED_LINE_HEIGHT,
  NET_ED_PAD,
  NET_ED_PAD_L,
  NET_ED_PAD_T,
  NET_CH_W_APPROX,
} from "./editorConstants.js";
import {
  getAC,
  catalogRowMatchesDeviceFamily,
  getLibraryTokenContext,
  mergeAutocompleteItems,
} from "./spiceAutocomplete.js";
import ComponentBrowser from "./ComponentBrowser.jsx";

/** Textarea + gutter + highlight overlay, autocomplete, library picker, inline AI. */
var KernelNetlistEditor = forwardRef(function KernelNetlistEditor(props, ref) {
  var net = props.net;
  var setNet = props.setNet;
  var apiBase = props.apiBase;
  var doSim = props.doSim;
  var doDRC = props.doDRC;
  var libCache = props.libCache;
  var circuitKey = props.circuitKey;
  var aiKey = props.aiKey;
  var onNeedAiKey = props.onNeedAiKey;
  var onUndo = props.onUndo;
  var onRedo = props.onRedo;

  var _ac = useState([]),
    acI = _ac[0],
    setAcI = _ac[1];
  var _aci = useState(-1),
    acIdx = _aci[0],
    setAcIdx = _aci[1];
  var _acp = useState({ x: 0, y: 0 }),
    acP = _acp[0],
    setAcP = _acp[1];
  var _aiShow = useState(false),
    aiShow = _aiShow[0],
    setAiShow = _aiShow[1];
  var _aiQ = useState(""),
    aiQ = _aiQ[0],
    setAiQ = _aiQ[1];
  var _aiGhost = useState(""),
    aiGhost = _aiGhost[0],
    setAiGhost = _aiGhost[1];
  var _aiBusy = useState(false),
    aiBusy = _aiBusy[0],
    setAiBusy = _aiBusy[1];
  var _aiLine = useState(0),
    aiLine = _aiLine[0],
    setAiLine = _aiLine[1];
  var _aiw = useState([]),
    aiWarnings = _aiw[0],
    setAiWarnings = _aiw[1];
  var _pk = useState(false),
    pickOpen = _pk[0],
    setPickOpen = _pk[1];
  var _pp = useState({ x: 80, y: 120 }),
    pickPos = _pp[0],
    setPickPos = _pp[1];
  var _pln = useState(1),
    pickLine = _pln[0],
    setPickLine = _pln[1];
  var _pse = useState(null),
    pickerSeedType = _pse[0],
    setPickerSeedType = _pse[1];
  var _nso = useState(false),
    netSelOverlayOff = _nso[0],
    setNetSelOverlayOff = _nso[1];

  var hlR = useRef(null),
    taR = useRef(null),
    gutterRef = useRef(null),
    aiRef = useRef(null);
  var acRemoteTRef = useRef(null);
  var acLibReqGenRef = useRef(0);
  var acInputDebounceRef = useRef(null);
  var lastAiCatalogTypesRef = useRef([]);

  var netDeferred = useDeferredValue(net);

  useEffect(
    function () {
      setAiShow(false);
      setAiGhost("");
      setAiQ("");
      setAiWarnings([]);
      setAcI([]);
      setAcIdx(-1);
      setPickOpen(false);
    },
    [circuitKey],
  );

  useEffect(function () {
    return function () {
      clearTimeout(acRemoteTRef.current);
      clearTimeout(acInputDebounceRef.current);
    };
  }, []);

  var syncNetSelOverlay = useCallback(function () {
    var ta = taR.current;
    if (!ta) {
      setNetSelOverlayOff(false);
      return;
    }
    setNetSelOverlayOff(document.activeElement === ta && ta.selectionStart !== ta.selectionEnd);
  }, []);
  useEffect(function () {
    document.addEventListener("selectionchange", syncNetSelOverlay);
    return function () {
      document.removeEventListener("selectionchange", syncNetSelOverlay);
    };
  }, [syncNetSelOverlay]);

  var showInlineAI = useCallback(
    function () {
      var ta = taR.current;
      if (!ta) return;
      if (!aiKey.trim()) {
        if (onNeedAiKey) onNeedAiKey();
        return;
      }
      setPickOpen(false);
      setAcI([]);
      setAcIdx(-1);
      setAiWarnings([]);
      var before = ta.value.slice(0, ta.selectionStart);
      var lineNum = before.split("\n").length;
      setAiLine(lineNum);
      setAiShow(true);
      setAiQ("");
      setAiGhost("");
      setTimeout(function () {
        if (aiRef.current) aiRef.current.focus();
      }, 50);
    },
    [aiKey, onNeedAiKey],
  );

  var doInlineAI = useCallback(
    function () {
      if (!aiQ.trim() || !aiKey.trim()) return;
      setAiBusy(true);
      setAiGhost("");
      setAiWarnings([]);
      if (libCache && libCache.ready) lastAiCatalogTypesRef.current = getResolvedCatalogTypesForQuery(libCache, aiQ);
      else lastAiCatalogTypesRef.current = [];
      var ta = taR.current;
      var cursorLine = aiLine;
      var prompt = buildInlineAIPrompt(
        {
          netlist: net,
          cursorLine: cursorLine,
          userRequest: aiQ,
          libCache: libCache,
        },
        { maxChars: 2600 },
      );

      var root = normalizeApiBase(apiBase);
      fetchOnce503Retry((root || "") + "/api/ai/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: aiKey, prompt: prompt, provider: "deepseek" }),
      })
        .then(function (r) {
          return r.json().then(function (d) {
            if (!r.ok) throw new Error(d.detail || "HTTP " + r.status);
            return d;
          });
        })
        .then(function (d) {
          var t = d.netlist_text || "";
          setAiGhost(t);
          if (t.indexOf("* Error") === 0) setAiWarnings([]);
          else if (libCache && libCache.ready) setAiWarnings(validateAIResponse(t, libCache).warnings || []);
          else setAiWarnings([]);
        })
        .catch(function (e) {
          setAiGhost("* Error: " + e.message);
          setAiWarnings([]);
        })
        .finally(function () {
          setAiBusy(false);
        });
    },
    [aiQ, aiKey, net, aiLine, apiBase, libCache],
  );

  var acceptGhost = useCallback(
    function () {
      if (!aiGhost) return;
      var lines = net.split("\n");
      lines.splice(aiLine, 0, aiGhost);
      setNet(lines.join("\n"));
      setAiShow(false);
      setAiGhost("");
      setAiQ("");
      setAiWarnings([]);
    },
    [aiGhost, net, aiLine, setNet],
  );

  var dismissAI = useCallback(function () {
    setAiShow(false);
    setAiGhost("");
    setAiQ("");
    setAiWarnings([]);
    if (taR.current) taR.current.focus();
  }, []);

  var openLibraryFromAI = useCallback(function () {
    setAiShow(false);
    setAiGhost("");
    setAiQ("");
    setAiWarnings([]);
    setPickLine(aiLine);
    setPickPos({
      x: Math.min(NET_ED_PAD_L + 32 * NET_CH_W_APPROX, 520),
      y: Math.min(NET_ED_PAD_T + aiLine * NET_ED_LINE_HEIGHT, 360),
    });
    var ts = lastAiCatalogTypesRef.current || [];
    setPickerSeedType(ts.length ? ts[0] : "");
    setPickOpen(true);
  }, [aiLine]);

  var updateAC2 = useCallback(
    function () {
      var ta = taR.current;
      if (!ta) {
        setAcI([]);
        setAcIdx(-1);
        return;
      }
      var text = ta.value,
        pos = ta.selectionStart;
      var before = text.slice(0, pos);
      var lines = before.split("\n");
      function place() {
        var curL = lines[lines.length - 1] || "";
        setAcP({
          x: NET_ED_PAD_L + curL.length * NET_CH_W_APPROX,
          y: NET_ED_PAD_T + lines.length * NET_ED_LINE_HEIGHT,
        });
      }
      var acItems = getAC(text, pos);
      var libCtx = getLibraryTokenContext(text, pos);
      var libLocal = [];
      if (libCache && libCache.ready && libCtx)
        libLocal = searchLocal(libCache, libCtx.query, { limit: 10 }).filter(function (r) {
          return catalogRowMatchesDeviceFamily(r, libCtx.deviceFamily);
        });
      var merged =
        libCtx && libCache && libCache.ready ? mergeAutocompleteItems(acItems, libLocal, []) : acItems;
      if (merged.length) {
        place();
        setAcI(merged);
        setAcIdx(0);
      } else {
        setAcI([]);
        setAcIdx(-1);
      }
      if (libCtx && libCache && libCache.ready && libCtx.query.length >= 2) {
        var needRemote =
          (libCtx.query.length >= 3 && libLocal.length < 3) ||
          (libCtx.query.length === 2 && libLocal.length === 0);
        if (needRemote) {
          var myGen = ++acLibReqGenRef.current;
          clearTimeout(acRemoteTRef.current);
          acRemoteTRef.current = setTimeout(function () {
            var root = normalizeApiBase(apiBase);
            searchRemote(root, libCtx.query, "", 20)
              .then(function (rows) {
                if (acLibReqGenRef.current !== myGen) return;
                var ta2 = taR.current;
                if (!ta2) return;
                var t2 = ta2.value,
                  p2 = ta2.selectionStart;
                if (t2 !== text || p2 !== pos) return;
                var b2 = getAC(t2, p2);
                var ctx2 = getLibraryTokenContext(t2, p2);
                if (!ctx2 || ctx2.query !== libCtx.query) return;
                var loc2 = searchLocal(libCache, ctx2.query, { limit: 10 }).filter(function (r) {
                  return catalogRowMatchesDeviceFamily(r, ctx2.deviceFamily);
                });
                var rem = (rows || []).filter(function (r) {
                  return catalogRowMatchesDeviceFamily(r, ctx2.deviceFamily);
                });
                var m2 = mergeAutocompleteItems(b2, loc2, rem);
                if (!m2.length) return;
                var bef2 = t2.slice(0, p2).split("\n");
                setAcP({
                  x: NET_ED_PAD_L + bef2[bef2.length - 1].length * NET_CH_W_APPROX,
                  y: NET_ED_PAD_T + bef2.length * NET_ED_LINE_HEIGHT,
                });
                setAcI(m2);
                setAcIdx(0);
              })
              .catch(function () {});
          }, 200);
        }
      }
    },
    [libCache, apiBase],
  );

  var applyAC2 = useCallback(
    function (item) {
      var ta = taR.current;
      if (!ta) return;
      var pos = ta.selectionStart;
      var text = ta.value;
      var snip = typeof item === "string" ? item : item && item.snip;
      var libRow = item && item.libRow;
      if (libRow) {
        var pn = String(libRow.part_number || "").trim();
        if (!pn) {
          setAcI([]);
          setAcIdx(-1);
          return;
        }
        var rep = replaceWordAtCursor(text, pos, pn);
        var blk = buildInsertBlock(rep.text, libRow);
        var nw = appendModelsBeforeEnd(rep.text, blk.modelBlock);
        setNet(nw);
        setTimeout(function () {
          ta.selectionStart = ta.selectionEnd = rep.newPos;
          ta.focus();
        }, 0);
      } else if (snip) {
        var wm = text.slice(0, pos).match(/[.\w]+$/);
        if (wm) {
          var start = pos - wm[0].length;
          var nw2 = text.slice(0, start) + snip + text.slice(pos);
          setNet(nw2);
          setTimeout(function () {
            ta.selectionStart = ta.selectionEnd = start + snip.length;
            ta.focus();
          }, 0);
        }
      }
      setAcI([]);
      setAcIdx(-1);
    },
    [setNet],
  );

  var openPicker = useCallback(
    function () {
      var ta = taR.current;
      if (!ta) return;
      setAcI([]);
      setAcIdx(-1);
      var before = ta.value.slice(0, ta.selectionStart);
      var lns = before.split("\n");
      setPickLine(lns.length);
      setPickPos({
        x: Math.min(NET_ED_PAD_L + lns[lns.length - 1].length * NET_CH_W_APPROX, 520),
        y: Math.min(NET_ED_PAD_T + lns.length * NET_ED_LINE_HEIGHT, 360),
      });
      setPickerSeedType(null);
      setPickOpen(true);
    },
    [],
  );

  var closeComponentBrowser = useCallback(function () {
    setPickOpen(false);
    setPickerSeedType(null);
  }, []);

  var onKeyDown = useCallback(
    function (e) {
      if (e.ctrlKey && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        if (onUndo) onUndo();
        return;
      }
      if (e.ctrlKey && (e.key === "y" || (e.shiftKey && e.key === "Z"))) {
        e.preventDefault();
        if (onRedo) onRedo();
        return;
      }
      if (e.key === "F5") {
        e.preventDefault();
        doSim();
        return;
      }
      if (e.ctrlKey && e.key === "d") {
        e.preventDefault();
        doDRC();
        return;
      }
      if (e.ctrlKey && (e.key === "l" || e.key === "L")) {
        e.preventDefault();
        if (pickOpen) closeComponentBrowser();
        else openPicker();
        return;
      }
      if (e.ctrlKey && (e.key === "i" || e.key === "k" || e.key === "I" || e.key === "K")) {
        e.preventDefault();
        showInlineAI();
        return;
      }
      if (e.ctrlKey && e.key === " ") {
        e.preventDefault();
        if (pickOpen) closeComponentBrowser();
        setTimeout(updateAC2, 0);
        return;
      }
      if (acI.length > 0) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setAcIdx(function (i) {
            return Math.min(i + 1, acI.length - 1);
          });
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setAcIdx(function (i) {
            return Math.max(i - 1, 0);
          });
          return;
        }
        if (e.key === "Enter" || e.key === "Tab") {
          if (acIdx >= 0 && acIdx < acI.length) {
            e.preventDefault();
            applyAC2(acI[acIdx]);
          }
          return;
        }
        if (e.key === "Escape") {
          setAcI([]);
          return;
        }
      }
    },
    [pickOpen, acI, acIdx, doSim, doDRC, showInlineAI, updateAC2, applyAC2, openPicker, closeComponentBrowser, onUndo, onRedo],
  );

  var onInput = useCallback(
    function (e) {
      setNet(e.target.value);
      clearTimeout(acInputDebounceRef.current);
      acInputDebounceRef.current = setTimeout(updateAC2, 60);
    },
    [setNet, updateAC2],
  );

  var sync = useCallback(
    function () {
      if (taR.current && hlR.current) {
        hlR.current.scrollTop = taR.current.scrollTop;
        hlR.current.scrollLeft = taR.current.scrollLeft;
      }
      if (taR.current && gutterRef.current) {
        gutterRef.current.scrollTop = taR.current.scrollTop;
      }
      if (pickOpen) closeComponentBrowser();
    },
    [pickOpen, closeComponentBrowser],
  );

  useImperativeHandle(
    ref,
    function () {
      return {
        focus: function () {
          if (taR.current) taR.current.focus();
        },
        cut: function () {
          var ta = taR.current;
          if (!ta) return;
          var s = ta.selectionStart,
            end = ta.selectionEnd;
          if (s === end) return;
          var sel = net.slice(s, end);
          navigator.clipboard.writeText(sel).catch(function () {});
          var nw = net.slice(0, s) + net.slice(end);
          setNet(nw);
          setTimeout(function () {
            ta.selectionStart = ta.selectionEnd = s;
            ta.focus();
            sync();
          }, 0);
        },
        copy: function () {
          var ta = taR.current;
          if (!ta) return;
          var s = ta.selectionStart,
            end = ta.selectionEnd;
          if (s === end) return;
          navigator.clipboard.writeText(net.slice(s, end)).catch(function () {});
        },
        paste: function () {
          navigator.clipboard.readText().then(function (text) {
            var ta = taR.current;
            if (!ta) return;
            var s = ta.selectionStart,
              end = ta.selectionEnd;
            var ins = String(text || "");
            var nw = net.slice(0, s) + ins + net.slice(end);
            setNet(nw);
            setTimeout(function () {
              ta.selectionStart = ta.selectionEnd = s + ins.length;
              ta.focus();
              sync();
            }, 0);
          });
        },
      };
    },
    [net, setNet, sync],
  );

  var netEdMono = {
    fontFamily: NET_ED_FONT,
    fontSize: NET_ED_FONT_SIZE,
    lineHeight: NET_ED_LINE_HEIGHT + "px",
    padding: NET_ED_PAD,
    tabSize: 4,
    MozTabSize: 4,
    boxSizing: "border-box",
    whiteSpace: "pre",
  };
  var lc = net.split("\n").length;

  var displayHL = useMemo(
    function () {
      if (!aiShow || !aiGhost) return hlS(netDeferred);
      var lines = net.split("\n");
      var before = lines.slice(0, aiLine);
      var after = lines.slice(aiLine);
      var ghostLines = aiGhost.split("\n").map(function (l) {
        return '<span class="vb-hl-ai">' + esc(l) + "</span>";
      });
      var allHL = before.map(function (l) {
        return hlS(l).split("\n")[0];
      });
      allHL = allHL.concat(ghostLines);
      allHL = allHL.concat(
        after.map(function (l) {
          return hlS(l).split("\n")[0];
        }),
      );
      return allHL.join("\n");
    },
    [net, netDeferred, aiShow, aiGhost, aiLine],
  );

  return (
    <div
      style={{
        border: "1px solid #A0A0A0",
        borderRadius: 4,
        overflow: "hidden",
        marginBottom: 12,
        boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        position: "relative",
        flex: 1,
        minHeight: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          background: "#E8E8E8",
          borderBottom: "1px solid #C8C8C8",
          padding: "2px 10px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: 11,
          color: "#666",
          flexShrink: 0,
        }}
      >
        <span style={{ fontWeight: 600 }}>SPICE Netlist</span>
        <span style={{ color: "#999", fontSize: 10 }}>
          File: Ctrl+O load Ctrl+S save | Ctrl+Z/Y undo redo | F5 run | Ctrl+D DRC | Ctrl+I/K AI | Ctrl+L library | Ctrl+Space AC | Esc
        </span>
      </div>
      <div
        style={{
          position: "relative",
          display: "flex",
          background: "#FFF",
          flex: 1,
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        <div
          ref={gutterRef}
          onScroll={function () {
            if (taR.current && gutterRef.current) {
              taR.current.scrollTop = gutterRef.current.scrollTop;
              sync();
            }
          }}
          style={{
            padding: NET_ED_PAD_T + "px 6px " + NET_ED_PAD_T + "px 4px",
            textAlign: "right",
            fontFamily: NET_ED_FONT,
            fontSize: NET_ED_FONT_SIZE,
            lineHeight: NET_ED_LINE_HEIGHT + "px",
            color: "#8C8C78",
            userSelect: "none",
            width: NET_GUTTER_PX,
            minWidth: NET_GUTTER_PX,
            maxWidth: NET_GUTTER_PX,
            flexShrink: 0,
            boxSizing: "border-box",
            background: "#F4F0E8",
            borderRight: "1px solid #D8D0C0",
            height: "100%",
            minHeight: 0,
            overflowX: "hidden",
            overflowY: "auto",
            overscrollBehavior: "contain",
          }}
        >
          {Array.from({ length: aiGhost && aiShow ? lc + aiGhost.split("\n").length : lc }, function (_, i) {
            return (
              <div
                key={i}
                style={{
                  background:
                    aiShow && i >= aiLine - 1 && i < aiLine - 1 + ((aiGhost || "").split("\n").length || 0)
                      ? "#E3F2FD"
                      : "transparent",
                }}
              >
                {i + 1}
              </div>
            );
          })}
        </div>
        <div
          style={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            position: "relative",
            overflow: "hidden",
          }}
        >
          <pre
            ref={hlR}
            style={Object.assign({}, netEdMono, {
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              pointerEvents: "none",
              color: "#000",
              margin: 0,
              zIndex: 1,
              opacity: netSelOverlayOff ? 0 : 1,
              overflow: "auto",
            })}
            dangerouslySetInnerHTML={{ __html: displayHL }}
          />
          <textarea
            ref={taR}
            value={net}
            onChange={onInput}
            onScroll={sync}
            onKeyDown={onKeyDown}
            onSelect={syncNetSelOverlay}
            onMouseUp={syncNetSelOverlay}
            onBlur={function () {
              setNetSelOverlayOff(false);
            }}
            onClick={function () {
              setAcI([]);
              setAcIdx(-1);
              setPickOpen(false);
              syncNetSelOverlay();
            }}
            spellCheck={false}
            style={Object.assign({}, netEdMono, {
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              width: "100%",
              height: "100%",
              margin: 0,
              background: netSelOverlayOff ? "#FFF" : "transparent",
              color: netSelOverlayOff ? "#111" : "transparent",
              caretColor: "#000",
              border: "none",
              outline: "none",
              resize: "none",
              zIndex: 2,
              overflow: "auto",
              boxSizing: "border-box",
            })}
          />
          {acI.length > 0 && (
            <div
              style={{
                position: "absolute",
                left: acP.x,
                top: acP.y,
                background: "#FFF",
                border: "1px solid #A0A0A0",
                borderRadius: 4,
                boxShadow: "0 3px 12px rgba(0,0,0,0.15)",
                zIndex: 100,
                minWidth: 260,
                maxHeight: 200,
                overflowY: "auto",
                fontSize: 12,
                fontFamily: "'Courier New',monospace",
              }}
            >
              {acI.map(function (item, i) {
                var badge = item.kind === "part" ? "PART" : String(item.kind || "").toUpperCase();
                return (
                  <div
                    key={i}
                    onClick={function () {
                      applyAC2(item);
                    }}
                    style={{
                      padding: "4px 10px",
                      cursor: "pointer",
                      background: i === acIdx ? "#D6E4F0" : "#FFF",
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      borderBottom: "1px solid #F5F5F5",
                    }}
                    onMouseEnter={function () {
                      setAcIdx(i);
                    }}
                  >
                    <span
                      style={{
                        fontSize: 8,
                        padding: "1px 4px",
                        borderRadius: 2,
                        background: kindBg[item.kind] || "#888",
                        color: "#FFF",
                        fontWeight: 700,
                      }}
                    >
                      {badge}
                    </span>
                    <span style={{ color: kindBg[item.kind] || "#333", fontWeight: "bold" }}>{item.word}</span>
                    <span style={{ color: "#999", fontSize: 11, marginLeft: "auto" }}>{item.desc}</span>
                  </div>
                );
              })}
              <div
                style={{
                  padding: "2px 10px",
                  fontSize: 9,
                  color: "#BBB",
                  background: "#F8F8F8",
                  borderTop: "1px solid #EEE",
                }}
              >
                Tab: insert + .model (parts) | Esc
              </div>
            </div>
          )}

          {pickOpen && (
            <ComponentBrowser
              visible={pickOpen}
              position={pickPos}
              insertAtLine1Based={pickLine}
              netlist={net}
              libCache={libCache}
              apiBase={apiBase}
              setNet={setNet}
              seedCompType={pickerSeedType || undefined}
              onClose={closeComponentBrowser}
            />
          )}

          {aiShow && (
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: NET_ED_PAD_T + (aiLine - 1) * NET_ED_LINE_HEIGHT,
                zIndex: 110,
                animation: "aiSlideIn 0.15s ease-out",
              }}
            >
              <div
                style={{
                  background: "#F0F7FF",
                  border: "1px solid #90CAF9",
                  borderRadius: 6,
                  margin: "0 8px",
                  boxShadow: "0 4px 16px rgba(21,101,192,0.15)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "4px 10px",
                    background: "#E3F2FD",
                    borderBottom: "1px solid #BBDEFB",
                    gap: 6,
                  }}
                >
                  <span style={{ fontSize: 10, fontWeight: 700, color: "#1565C0", letterSpacing: ".5px" }}>
                    AI ASSIST
                  </span>
                  <span style={{ fontSize: 10, color: "#64B5F6" }}>Ctrl+I</span>
                  <span style={{ marginLeft: "auto", fontSize: 10, color: "#999", cursor: "pointer" }} onClick={dismissAI}>
                    Esc to close
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", padding: "4px 8px", gap: 4 }}>
                  <span style={{ color: "#1565C0", fontSize: 14, fontWeight: "bold" }}>{">"}</span>
                  <input
                    ref={aiRef}
                    value={aiQ}
                    onChange={function (e) {
                      setAiQ(e.target.value);
                    }}
                    onKeyDown={function (e) {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        doInlineAI();
                      }
                      if (e.key === "Escape") {
                        e.preventDefault();
                        dismissAI();
                      }
                      if (e.key === "Tab" && aiGhost) {
                        e.preventDefault();
                        acceptGhost();
                      }
                    }}
                    placeholder="Describe what to add... (Enter to ask, Tab to accept)"
                    style={{
                      flex: 1,
                      fontSize: 12,
                      padding: "4px 6px",
                      border: "1px solid #BBDEFB",
                      borderRadius: 3,
                      background: "#FFF",
                      outline: "none",
                      fontFamily: "'Segoe UI',sans-serif",
                      color: "#333",
                    }}
                  />
                  <button
                    onClick={doInlineAI}
                    disabled={aiBusy || !aiQ.trim()}
                    style={{
                      fontSize: 10,
                      padding: "3px 10px",
                      borderRadius: 3,
                      border: "1px solid " + (aiBusy ? "#DDD" : "#1565C0"),
                      background: aiBusy ? "#EEE" : "#1565C0",
                      color: aiBusy ? "#999" : "#FFF",
                      cursor: aiBusy ? "not-allowed" : "pointer",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {aiBusy ? "Thinking..." : "Ask"}
                  </button>
                </div>
                {aiGhost && (
                  <div style={{ padding: "4px 10px 6px", borderTop: "1px solid #E3F2FD" }}>
                    <pre
                      style={{
                        fontSize: 12,
                        fontFamily: "'Courier New',monospace",
                        color: "#1565C0",
                        background: "#F0F7FF",
                        margin: 0,
                        whiteSpace: "pre-wrap",
                        lineHeight: "20px",
                      }}
                    >
                      {aiGhost}
                    </pre>
                    {aiWarnings.length > 0 && (
                      <div
                        style={{
                          marginTop: 6,
                          padding: "6px 8px",
                          background: "#FFFDE7",
                          border: "1px solid #FFE082",
                          borderRadius: 4,
                          fontSize: 10,
                          color: "#856404",
                        }}
                      >
                        {aiWarnings.slice(0, 3).map(function (w, i) {
                          return (
                            <div key={i}>
                              {"\u26A0 "}
                              {w}
                            </div>
                          );
                        })}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                      <button
                        onClick={acceptGhost}
                        style={{
                          fontSize: 11,
                          padding: "3px 12px",
                          borderRadius: 3,
                          border: "1px solid #2E7D32",
                          background: "#2E7D32",
                          color: "#FFF",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                      >
                        Accept (Tab)
                      </button>
                      <button
                        type="button"
                        onClick={openLibraryFromAI}
                        style={{
                          fontSize: 11,
                          padding: "3px 12px",
                          borderRadius: 3,
                          border: "1px solid #1565C0",
                          background: "#FFF",
                          color: "#1565C0",
                          cursor: "pointer",
                          fontWeight: 600,
                        }}
                      >
                        Open library (Ctrl+L)
                      </button>
                      <button
                        onClick={dismissAI}
                        style={{
                          fontSize: 11,
                          padding: "3px 12px",
                          borderRadius: 3,
                          border: "1px solid #B0B0B0",
                          background: "#FFF",
                          color: "#666",
                          cursor: "pointer",
                        }}
                      >
                        Dismiss (Esc)
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
});
export default KernelNetlistEditor;
