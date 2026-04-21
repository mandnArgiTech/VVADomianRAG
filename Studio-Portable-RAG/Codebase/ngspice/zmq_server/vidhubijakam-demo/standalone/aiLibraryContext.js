import { buildLibraryContextForAI } from "./libraryCache.js";

/**
 * D5EX-88D — Query-aware AI library context + response validation.
 */

/** @param {string} query */
export function detectRelevantTypes(query) {
  var q = String(query || "").toLowerCase();
  var types = [];
  var keywords = {
    MOSFET: [
      "mosfet",
      "nmos",
      "pmos",
      "n-channel",
      "p-channel",
      "fet",
      "switch",
      "power switch",
      "sic",
      "silicon carbide",
      "cascode",
    ],
    BJT: ["bjt", "transistor", "npn", "pnp", "amplifier", "gain stage", "darlington"],
    DIODE: ["diode", "rectifier", "schottky", "zener", "clamp", "protection", "tvs"],
    LED: ["led", "indicator", "light"],
    RESISTOR: ["resistor", "feedback", "bias", "pullup", "pull-up", "pulldown", "divider"],
    CAPACITOR: ["capacitor", "cap", "bypass", "decoupling", "filter", "smoothing", "coupling"],
    INDUCTOR: ["inductor", "choke", "coil", "filter inductor"],
    IGBT: ["igbt", "insulated gate"],
    JFET: ["jfet", "j-fet"],
    OPAMP: ["opamp", "op-amp", "operational amplifier", "comparator"],
  };
  Object.keys(keywords).forEach(function (type) {
    keywords[type].forEach(function (kw) {
      if (q.indexOf(kw) >= 0 && types.indexOf(type) < 0) types.push(type);
    });
  });
  if (types.length === 0) types = ["MOSFET", "BJT", "DIODE", "RESISTOR", "CAPACITOR"];
  return types;
}

/**
 * Map logical keywords to catalog comp_type keys present in cache.
 * @param {string[]} keywords from detectRelevantTypes
 * @param {{type:string,count:number}[]} cacheTypeRows
 */
export function resolveCatalogTypesForKeywords(keywords, cacheTypeRows) {
  var rows = cacheTypeRows || [];
  var out = [];
  function add(t) {
    if (t && out.indexOf(t) < 0) out.push(t);
  }
  keywords.forEach(function (kw) {
    var up = String(kw || "").toUpperCase();
    rows.forEach(function (row) {
      var t = String(row.type || "").toUpperCase();
      if (!t) return;
      if (up === "MOSFET" && (t.indexOf("MOSFET") >= 0 || (t.indexOf("SIC") >= 0 && t.indexOf("MOS") >= 0)))
        add(row.type);
      else if (up === "BJT" && (t.indexOf("BJT") >= 0 || t.indexOf("NPN") >= 0 || t.indexOf("PNP") >= 0))
        add(row.type);
      else if ((up === "DIODE" || up === "LED") && (t.indexOf("DIODE") >= 0 || t.indexOf("LED") >= 0 || t.indexOf("SCHOTTKY") >= 0 || t.indexOf("ZENER") >= 0))
        add(row.type);
      else if (up === "RESISTOR" && (t.indexOf("RESISTOR") >= 0 || t === "R")) add(row.type);
      else if (up === "CAPACITOR" && t.indexOf("CAP") >= 0) add(row.type);
      else if (up === "INDUCTOR" && (t.indexOf("IND") >= 0 || t.indexOf("INDUCTOR") >= 0)) add(row.type);
      else if (up === "IGBT" && t.indexOf("IGBT") >= 0) add(row.type);
      else if (up === "JFET" && t.indexOf("JFET") >= 0) add(row.type);
      else if (up === "OPAMP" && t.indexOf("OPAMP") >= 0) add(row.type);
    });
  });
  return out;
}

function briefSpecsLine(part) {
  var specs = part.specs || {};
  var brief = [];
  var VDS = specs.VDS != null ? specs.VDS : specs.Vds;
  var IDS = specs.IDS != null ? specs.IDS : specs.Ids != null ? specs.Ids : specs.Id;
  if (VDS != null) brief.push("VDS=" + VDS + "V");
  if (IDS != null) brief.push("IDS=" + IDS + "A");
  if (specs.BV != null) brief.push("BV=" + specs.BV + "V");
  if (specs.BF != null || specs.hFE != null) brief.push("hFE=" + (specs.BF != null ? specs.BF : specs.hFE));
  if (specs.VTO != null) brief.push("Vth=" + specs.VTO + "V");
  return brief.length ? " (" + brief.join(", ") + ")" : "";
}

/**
 * @param {*} cache library cache from initLibraryCache
 * @param {string} userQuery
 * @param {{ maxChars?: number, maxPerType?: number }} [opts]
 */
export function buildTypedLibraryContextForQuery(cache, userQuery, opts) {
  opts = opts || {};
  if (!cache || !cache.ready || !String(userQuery || "").trim()) return "";
  var maxChars = opts.maxChars != null ? opts.maxChars : 2800;
  var maxPerType = opts.maxPerType != null ? opts.maxPerType : 8;
  var kws = detectRelevantTypes(userQuery);
  var resolvedTypes = resolveCatalogTypesForKeywords(kws, cache.types || []);
  if (!resolvedTypes.length) resolvedTypes = (cache.types || []).slice(0, 6).map(function (r) {
    return r.type;
  });
  var sections = [];
  var budget = 0;
  for (var i = 0; i < resolvedTypes.length && budget < maxChars; i++) {
    var typ = resolvedTypes[i];
    var parts = (cache.topParts[typ] || []).slice(0, maxPerType);
    if (!parts.length) continue;
    var lines = parts.map(function (p) {
      var pl = p.part_number || "?";
      var sp = briefSpecsLine(p);
      var mfr = p.manufacturer ? " [" + p.manufacturer + "]" : "";
      var pay = String(p.spice_payload || "").replace(/\s+/g, " ").trim();
      if (pay.length > 220) pay = pay.slice(0, 217) + "…";
      var payBit = pay ? "\n    spice_payload: " + pay : "";
      return "  - " + pl + ": " + (p.comp_type || typ) + sp + mfr + payBit;
    });
    var block = typ + " parts available:\n" + lines.join("\n");
    if (budget + block.length > maxChars) {
      block = block.slice(0, maxChars - budget - 20) + "\n  …";
    }
    sections.push(block);
    budget += block.length;
  }
  if (!sections.length) return "";
  return sections.join("\n\n");
}

/**
 * Full inline-AI prompt: library-first, netlist sections, user request, unified RULES (D5EX-88D).
 * @param {{ netlist: string, cursorLine: number, userRequest: string, libCache: object|null }} opts
 * @param {{ maxChars?: number, maxPerType?: number }} [ctxOpts] — passed to typed catalog builder
 */
export function buildInlineAIPrompt(opts, ctxOpts) {
  opts = opts || {};
  ctxOpts = ctxOpts || {};
  var net = String(opts.netlist || "");
  var line = Math.max(0, Number(opts.cursorLine) || 0);
  var userRequest = String(opts.userRequest || "").trim();
  var libCache = opts.libCache;
  var lines = net.split("\n");
  var before = lines.slice(0, line).join("\n");
  var after = lines.slice(line).join("\n");
  var libSection = "";
  if (libCache && libCache.ready) {
    var typedBody = buildTypedLibraryContextForQuery(libCache, userRequest, ctxOpts);
    if (typedBody) {
      libSection =
        "=== COMPONENT LIBRARY (use ONLY these real part_numbers when naming models) ===\n" +
        typedBody +
        "\n\n";
    } else {
      var fb = buildLibraryContextForAI(libCache);
      if (fb)
        libSection = "=== COMPONENT LIBRARY (use these real part_numbers when applicable) ===\n" + fb + "\n\n";
    }
  }
  var rules = [
    "=== RULES ===",
    "1. Use ONLY real part numbers from the COMPONENT LIBRARY above when naming a device from the catalog.",
    "2. For catalog parts, include the .model/.subckt line using library spice_payload when you name a listed part.",
    "3. For plain values (e.g. 10k resistor, 100nF cap), use R n1 n2 10k / C n1 n2 100n without inventing a catalog part.",
    "4. Output ONLY raw SPICE lines to INSERT at the cursor — no markdown, no backticks, no explanations.",
    "5. Use correct SPICE syntax: device prefix + id + nodes + model name or value.",
    "6. Choose the most appropriate catalog part for the user's requirement when a specific part is not named.",
  ].join("\n");
  return [
    "You are a SPICE netlist expert helping an engineer edit their circuit.",
    "",
    libSection,
    "=== CURRENT NETLIST (before cursor, line " + line + ") ===",
    before,
    "",
    "=== NETLIST (after cursor) ===",
    after,
    "",
    "=== USER REQUEST ===",
    userRequest,
    "",
    rules,
    "",
  ].join("\n");
}

/** SPICE built-in / primitive .model names — not vendor part numbers. */
var SPICE_BUILTIN_MODEL_NAMES = {
  NPN: 1,
  PNP: 1,
  NMOS: 1,
  PMOS: 1,
  D: 1,
  DIODE: 1,
  NJF: 1,
  PJF: 1,
  NJFET: 1,
  PJFET: 1,
  NMF: 1,
  PMF: 1,
  R: 1,
  C: 1,
  L: 1,
  SW: 1,
  CSW: 1,
  URC: 1,
  LTRA: 1,
  CORE: 1,
};

/** Build uppercase set of known part_numbers from cache (flat index + topParts buckets). */
export function buildKnownPartNumberSet(cache) {
  var set = {};
  if (!cache || !cache.ready) return set;
  (cache.flatIndex || []).forEach(function (e) {
    if (e.pnUpper) set[e.pnUpper] = 1;
  });
  var tp = cache.topParts || {};
  Object.keys(tp).forEach(function (k) {
    (tp[k] || []).forEach(function (p) {
      var pn = String((p && p.part_number) || "")
        .trim()
        .toUpperCase();
      if (pn) set[pn] = 1;
    });
  });
  return set;
}

/**
 * @param {string} responseText
 * @param {*} cache
 * @returns {{ warnings: string[] }}
 */
/** Catalog type strings to pre-select in the library picker after AI. */
export function getResolvedCatalogTypesForQuery(cache, userQuery) {
  if (!cache || !cache.ready) return [];
  return resolveCatalogTypesForKeywords(detectRelevantTypes(userQuery), cache.types || []);
}

/** Strip trailing $... and ;... SPICE comments for instance-line heuristics. */
function stripSpiceLineComment(line) {
  var s = String(line || "").split("$")[0];
  var i = s.indexOf(";");
  if (i >= 0) s = s.slice(0, i);
  return s.trim();
}

/**
 * Last token that is likely a model/part name (not a value, not key=value).
 * Catches hallucinated instance lines without a matching .model in the ghost.
 */
function lastModelLikeTokenFromDeviceLine(line) {
  var s = stripSpiceLineComment(line);
  if (!s || s.charAt(0) === "." || s.charAt(0) === "*") return null;
  var parts = s.split(/\s+/).filter(Boolean);
  if (parts.length < 2) return null;
  var dev = parts[0];
  var c0 = dev.charAt(0).toUpperCase();
  if (c0 === "R" || c0 === "C" || c0 === "L") {
    if (parts.length < 4) return null;
    var last = parts[parts.length - 1];
    if (/^[\d.]/.test(last) || last.indexOf("(") >= 0) return null;
    return last;
  }
  if ("DQXJM".indexOf(c0) >= 0) {
    for (var i = parts.length - 1; i >= 1; i--) {
      var t = parts[i];
      if (t.indexOf("=") >= 0) continue;
      if (/^[\d.+-]+[eE]?[\d+-]*$/i.test(t)) continue;
      if (!/[A-Za-z_]/.test(t)) continue;
      return t;
    }
  }
  return null;
}

export function validateAIResponse(responseText, cache) {
  var warnings = [];
  if (!responseText || !cache || !cache.ready) return { warnings: warnings };
  var known = buildKnownPartNumberSet(cache);
  var seen = {};
  var lines = String(responseText).split("\n");
  lines.forEach(function (line) {
    var m = line.match(/^\s*\.model\s+(\S+)/i);
    if (m) {
      var pn = String(m[1] || "").toUpperCase();
      if (pn && !SPICE_BUILTIN_MODEL_NAMES[pn] && !known[pn]) {
        var w = ".model " + m[1] + " — not found in indexed library (verify parameters).";
        if (!seen[w]) {
          seen[w] = 1;
          warnings.push(w);
        }
      }
    }
    var s = line.match(/^\s*\.subckt\s+(\S+)/i);
    if (s) {
      var sn = String(s[1] || "").toUpperCase();
      if (sn && !known[sn]) {
        var w2 = ".subckt " + s[1] + " — not found in indexed library.";
        if (!seen[w2]) {
          seen[w2] = 1;
          warnings.push(w2);
        }
      }
    }
  });
  lines.forEach(function (line) {
    var tok = lastModelLikeTokenFromDeviceLine(line);
    if (!tok) return;
    var up = String(tok).toUpperCase();
    if (SPICE_BUILTIN_MODEL_NAMES[up]) return;
    if (known[up]) return;
    var w3 = "Device line references unknown model/part '" + tok + "' — not in indexed library.";
    if (!seen[w3]) {
      seen[w3] = 1;
      warnings.push(w3);
    }
  });
  return { warnings: warnings.slice(0, 5) };
}
