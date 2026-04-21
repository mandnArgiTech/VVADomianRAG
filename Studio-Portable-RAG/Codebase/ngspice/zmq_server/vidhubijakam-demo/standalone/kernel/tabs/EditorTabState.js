/** @typedef {{ id: string, label: string, net: string, an: string, circuitKey: string, dirty: boolean, selP: string | null, editorNonce: number, undoStack?: string[], redoStack?: string[] }} EditorTab */

var MAX_UNDO = 40;

var _tabId = 0;
function newTabId() {
  _tabId += 1;
  return "tab_" + _tabId;
}

/**
 * @param {string} initialNet
 * @param {string} initialAn
 * @param {{ label?: string, selP?: string | null }} [opts]
 */
export function createTabsState(initialNet, initialAn, opts) {
  var label = (opts && opts.label) || "Circuit";
  var selP = opts && opts.selP != null ? opts.selP : null;
  var id = newTabId();
  return {
    tabs: [
      {
        id: id,
        label: label,
        net: initialNet,
        an: initialAn,
        circuitKey: String(selP != null ? selP : id) + ":0",
        dirty: false,
        selP: selP,
        editorNonce: 0,
        undoStack: [],
        redoStack: [],
      },
    ],
    activeId: id,
  };
}

/**
 * @param {{ tabs: EditorTab[], activeId: string }} state
 * @param {{ type: string, payload?: any }} action
 */
export function tabsReducer(state, action) {
  var tabs = state.tabs;
  var activeId = state.activeId;

  function activeIndex() {
    return tabs.findIndex(function (t) {
      return t.id === activeId;
    });
  }

  function withTab(id, fn) {
    return tabs.map(function (t) {
      return t.id === id ? fn(t) : t;
    });
  }

  if (action.type === "ADD_TAB") {
    var nid = newTabId();
    var src = tabs[activeIndex()] || tabs[0];
    var baseNet = src ? src.net : "";
    var baseAn = src ? src.an : "op";
    var nt = {
      id: nid,
      label: "Untitled",
      net: baseNet,
      an: baseAn,
      circuitKey: nid + ":0",
      dirty: false,
      selP: null,
      editorNonce: 0,
      undoStack: [],
      redoStack: [],
    };
    return { tabs: tabs.concat([nt]), activeId: nid };
  }

  if (action.type === "CLOSE_TAB") {
    var closeId = action.payload && action.payload.id;
    if (!closeId || tabs.length <= 1) return state;
    var ix = tabs.findIndex(function (t) {
      return t.id === closeId;
    });
    if (ix < 0) return state;
    var nextTabs = tabs.filter(function (t) {
      return t.id !== closeId;
    });
    var nextActive = activeId;
    if (activeId === closeId) {
      var ni = Math.min(ix, nextTabs.length - 1);
      nextActive = nextTabs[Math.max(0, ni)].id;
    }
    return { tabs: nextTabs, activeId: nextActive };
  }

  if (action.type === "SELECT_TAB") {
    var sid = action.payload && action.payload.id;
    if (!sid || !tabs.some(function (t) {
      return t.id === sid;
    }))
      return state;
    return { tabs: tabs, activeId: sid };
  }

  if (action.type === "UPDATE_NET") {
    var net = action.payload && action.payload.net;
    if (typeof net !== "string") return state;
    return {
      tabs: withTab(activeId, function (t) {
        if (net === t.net) return t;
        var prev = t.net;
        var us = (t.undoStack || []).concat([prev]).slice(-MAX_UNDO);
        return Object.assign({}, t, {
          net: net,
          dirty: true,
          undoStack: us,
          redoStack: [],
        });
      }),
      activeId: activeId,
    };
  }

  if (action.type === "UNDO_NET") {
    return {
      tabs: withTab(activeId, function (t) {
        var us = t.undoStack || [];
        if (us.length === 0) return t;
        var prev = us[us.length - 1];
        var newUs = us.slice(0, -1);
        var rs = (t.redoStack || []).concat([t.net]);
        var nonce = t.editorNonce + 1;
        return Object.assign({}, t, {
          net: prev,
          undoStack: newUs,
          redoStack: rs,
          dirty: true,
          editorNonce: nonce,
          circuitKey: String(t.selP != null ? t.selP : activeId) + ":" + nonce,
        });
      }),
      activeId: activeId,
    };
  }

  if (action.type === "REDO_NET") {
    return {
      tabs: withTab(activeId, function (t) {
        var rs = t.redoStack || [];
        if (rs.length === 0) return t;
        var next = rs[rs.length - 1];
        var newRs = rs.slice(0, -1);
        var us = (t.undoStack || []).concat([t.net]).slice(-MAX_UNDO);
        var nonce = t.editorNonce + 1;
        return Object.assign({}, t, {
          net: next,
          undoStack: us,
          redoStack: newRs,
          dirty: true,
          editorNonce: nonce,
          circuitKey: String(t.selP != null ? t.selP : activeId) + ":" + nonce,
        });
      }),
      activeId: activeId,
    };
  }

  if (action.type === "SET_AN") {
    var an = action.payload && action.payload.an;
    if (typeof an !== "string") return state;
    var al = an.trim().toLowerCase();
    if (!/^(op|ac|tran|dc)$/.test(al)) return state;
    return {
      tabs: withTab(activeId, function (t) {
        return Object.assign({}, t, { an: al });
      }),
      activeId: activeId,
    };
  }

  if (action.type === "TAB_LOAD_FROM_CATALOG") {
    var p = action.payload || {};
    var net = p.net;
    var an = p.an;
    var label = p.label;
    var selP = p.selP;
    if (typeof net !== "string") return state;
    return {
      tabs: withTab(activeId, function (t) {
        var nonce = t.editorNonce + 1;
        var sp = selP !== undefined ? selP : t.selP;
        return Object.assign({}, t, {
          net: net,
          an: typeof an === "string" ? an : t.an,
          label: typeof label === "string" ? label : t.label,
          selP: sp,
          dirty: false,
          editorNonce: nonce,
          circuitKey: String(sp != null ? sp : activeId) + ":" + nonce,
          undoStack: [],
          redoStack: [],
        });
      }),
      activeId: activeId,
    };
  }

  if (action.type === "OPEN_TAB_WITH_CIRCUIT") {
    var op = action.payload || {};
    var onet = op.net;
    if (typeof onet !== "string") return state;
    var oan = typeof op.an === "string" ? op.an.trim().toLowerCase() : "op";
    if (!/^(op|ac|tran|dc)$/.test(oan)) oan = "op";
    var olab = typeof op.label === "string" && op.label.trim() ? op.label.trim() : "Circuit";
    var osp = op.selP !== undefined ? op.selP : null;
    var onid = newTabId();
    var ont = {
      id: onid,
      label: olab,
      net: onet,
      an: oan,
      circuitKey: String(osp != null ? osp : onid) + ":0",
      dirty: false,
      selP: osp,
      editorNonce: 0,
      undoStack: [],
      redoStack: [],
    };
    return { tabs: tabs.concat([ont]), activeId: onid };
  }

  if (action.type === "MARK_ACTIVE_SAVED") {
    var mp = action.payload || {};
    return {
      tabs: withTab(activeId, function (t) {
        var u = Object.assign({}, t, { dirty: false });
        if (typeof mp.selP === "string") u.selP = mp.selP;
        if (typeof mp.label === "string" && mp.label.trim()) u.label = mp.label.trim();
        return u;
      }),
      activeId: activeId,
    };
  }

  if (action.type === "SYNC_CATALOG_TO_ACTIVE") {
    var cnet = action.payload && action.payload.net;
    var can = action.payload && action.payload.an;
    var csel = action.payload && action.payload.selP;
    var clabel = action.payload && action.payload.label;
    if (typeof cnet !== "string") return state;
    return {
      tabs: withTab(activeId, function (t) {
        return Object.assign({}, t, {
          net: cnet,
          an: typeof can === "string" ? can : t.an,
          selP: csel !== undefined ? csel : t.selP,
          label: typeof clabel === "string" ? clabel : t.label,
          dirty: false,
          circuitKey: String(csel != null ? csel : t.selP || activeId) + ":0",
          editorNonce: 0,
          undoStack: [],
          redoStack: [],
        });
      }),
      activeId: activeId,
    };
  }

  return state;
}

/**
 * @param {{ tabs: EditorTab[], activeId: string }} state
 * @returns {EditorTab | null}
 */
export function getActiveTab(state) {
  return state.tabs.find(function (t) {
    return t.id === state.activeId;
  }) || null;
}
