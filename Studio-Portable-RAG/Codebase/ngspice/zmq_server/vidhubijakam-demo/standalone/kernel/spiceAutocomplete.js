import { AC_CMP, AC_DIR, AC_PAR, AC_SRC, AC_TYP } from "./spiceAutocompleteData.js";

export function getAC(text, pos) {
  var before = text.slice(0, pos);
  var ls = before.lastIndexOf("\n") + 1;
  var line = before.slice(ls);
  var wm = line.match(/[.\w]+$/);
  if (!wm || wm[0].length < 1) return [];
  var w = wm[0],
    wu = w.toUpperCase();
  var r = [];
  if (w.startsWith(".")) {
    AC_DIR.forEach(function (d) {
      if (d.w.toUpperCase().startsWith(wu) && d.w.toUpperCase() !== wu)
        r.push({ word: d.w, desc: d.d, snip: d.s, kind: "dir" });
    });
    return r.slice(0, 10);
  }
  if (/\.model\s+\S+\s+\S*$/i.test(line)) {
    AC_TYP.forEach(function (m) {
      if (m.w.toUpperCase().startsWith(wu)) r.push({ word: m.w, desc: m.d, snip: m.w, kind: "typ" });
    });
    return r.slice(0, 10);
  }
  var mm = line.match(/\.model\s+\S+\s+(NPN|PNP|NMOS|PMOS|D)\s*\(/i);
  if (mm) {
    (AC_PAR[mm[1].toUpperCase()] || []).forEach(function (p) {
      if (p.toUpperCase().startsWith(wu)) r.push({ word: p + "=", desc: mm[1] + " param", snip: p + "=", kind: "par" });
    });
    return r.slice(0, 10);
  }
  if (/^[VI]\S*\s+\S+\s+\S+\s+\S*$/i.test(line)) {
    AC_SRC.forEach(function (s) {
      if (s.w.toUpperCase().startsWith(wu)) r.push({ word: s.w, desc: s.d, snip: s.snip || s.s, kind: "src" });
    });
    if (r.length) return r.slice(0, 10);
  }
  if (line.trimLeft() === w && w.length <= 2) {
    AC_CMP.forEach(function (c) {
      if (c.w.toUpperCase().startsWith(wu)) r.push({ word: c.w, desc: c.d, snip: c.s, kind: "cmp" });
    });
    return r.slice(0, 10);
  }
  var nodes = {};
  text.split("\n").forEach(function (l) {
    var p = l.trim().split(/\s+/);
    if (p.length >= 3 && /^[RCLVIDEQMJXKFGH]/i.test(p[0])) {
      if (p[1]) nodes[p[1]] = 1;
      if (p[2]) nodes[p[2]] = 1;
    }
  });
  Object.keys(nodes).forEach(function (n) {
    if (n.toUpperCase().startsWith(wu) && n.toUpperCase() !== wu) r.push({ word: n, desc: "node", snip: n, kind: "nod" });
  });
  return r.slice(0, 10);
}

/** Catalog comp_type strings use MOSFET_N, BJT_NPN, DIODE_*, SUBCKT, etc. */
export function catalogRowMatchesDeviceFamily(row, fam) {
  var ct = String(row.comp_type || "").toUpperCase();
  var pl = String(row.spice_payload || "").trim();
  if (fam === "M") return ct.indexOf("MOSFET") >= 0;
  if (fam === "Q") return ct.indexOf("BJT") >= 0 || ct.indexOf("NPN") >= 0 || ct.indexOf("PNP") >= 0;
  if (fam === "D") return ct.indexOf("DIODE") >= 0 || ct.indexOf("LED") >= 0;
  if (fam === "J") return ct.indexOf("JFET") >= 0;
  if (fam === "R") return ct.indexOf("RESISTOR") >= 0 || ct === "R";
  if (fam === "X") return ct.indexOf("SUB") >= 0 || /^\.subckt/i.test(pl);
  return true;
}

/** D5EX-88B — one-line brief for autocomplete (specs when present). */
export function formatPartBrief(row) {
  if (!row) return "";
  var specs = row.specs || {};
  var brief = [];
  var VDS = specs.VDS != null ? specs.VDS : specs.Vds;
  var IDS = specs.IDS != null ? specs.IDS : specs.Ids != null ? specs.Ids : specs.Id;
  if (VDS != null) brief.push(String(VDS) + "V");
  if (IDS != null) brief.push(String(IDS) + "A");
  if (specs.BV != null) brief.push("BV=" + specs.BV + "V");
  if (specs.BF != null || specs.hFE != null) brief.push("hFE=" + (specs.BF != null ? specs.BF : specs.hFE));
  if (specs.VTO != null) brief.push("Vth=" + specs.VTO + "V");
  var core = brief.length
    ? brief.join(" ")
    : String(row.description || row.comp_type || "")
        .replace(/\s+/g, " ")
        .slice(0, 40);
  var mfr = row.manufacturer ? " · " + row.manufacturer : "";
  return core + mfr;
}

/** Trailing token is almost certainly a numeric value, not a part number (R lines). */
export function looksLikeSpiceNumericValue(tok) {
  return /^[0-9]*\.?[0-9]+[fpnumkMGT]?$/i.test(String(tok || "").trim());
}

/** Cursor is typing a device model name token; return { query, deviceFamily } or null. */
export function getLibraryTokenContext(text, pos) {
  var before = text.slice(0, pos);
  var ls = before.lastIndexOf("\n") + 1;
  var line = before.slice(ls);
  var wm = line.match(/[.\w]+$/);
  if (!wm || wm[0].length < 2) return null;
  var w = wm[0];
  var raw = line.trim().split(";")[0].trim();
  if (!raw || raw.charAt(0) === "*") return null;
  if (/^\s*\./.test(raw)) return null;
  var t = raw.split(/\s+/);
  if (t.length < 2) return null;
  var last = t[t.length - 1];
  if (last !== w) return null;
  var c0 = t[0].charAt(0).toUpperCase();
  var fam = "";
  if (c0 === "M" && t.length >= 6) fam = "M";
  else if (c0 === "Q" && t.length >= 5) fam = "Q";
  else if (c0 === "D" && t.length >= 4) fam = "D";
  else if (c0 === "J" && t.length >= 5) fam = "J";
  else if (c0 === "R" && t.length >= 4) fam = "R";
  else if (c0 === "X" && t.length >= 4) fam = "X";
  else return null;
  if (fam === "R" && looksLikeSpiceNumericValue(w)) return null;
  return { query: w, deviceFamily: fam, deviceLetter: c0 };
}

/** Merge SPICE AC with library hits (library first). */
export function mergeAutocompleteItems(baseItems, libLocal, libRemote) {
  var seen = {};
  var libPnUpper = {};
  var out = [];
  function kLib(r) {
    return "L:" + String(r.part_number || "");
  }
  function add(item, key) {
    if (!item || seen[key] || out.length >= 12) return;
    seen[key] = 1;
    out.push(item);
  }
  (libLocal || []).forEach(function (r) {
    if (!r || !r.part_number) return;
    libPnUpper[String(r.part_number).toUpperCase()] = 1;
    add(
      { word: r.part_number, desc: formatPartBrief(r), snip: r.part_number, kind: "part", libRow: r },
      kLib(r),
    );
  });
  (libRemote || []).forEach(function (r) {
    if (!r || !r.part_number) return;
    libPnUpper[String(r.part_number).toUpperCase()] = 1;
    add(
      { word: r.part_number, desc: formatPartBrief(r), snip: r.part_number, kind: "part", libRow: r },
      kLib(r),
    );
  });
  (baseItems || []).forEach(function (it) {
    if (!it || !it.word) return;
    if (libPnUpper[String(it.word).toUpperCase()]) return;
    add(it, "B:" + it.word);
  });
  return out;
}
