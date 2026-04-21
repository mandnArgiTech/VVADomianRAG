/**
 * SPICE line + .model generation for catalog rows (D5EX-88 Phase E).
 */

function netHasModelForPart(netlist, partNumber) {
  var pn = String(partNumber || "").trim();
  if (!pn) return false;
  var esc = pn.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  var re = new RegExp("^\\s*\\.model\\s+" + esc + "\\b", "im");
  return re.test(netlist);
}

function netHasSubckt(netlist, partNumber) {
  var pn = String(partNumber || "").trim();
  if (!pn) return false;
  var esc = pn.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  var re = new RegExp("^\\s*\\.subckt\\s+" + esc + "\\b", "im");
  return re.test(netlist);
}

/** Next numeric id for R1-style prefix (letter + digits). */
export function nextDeviceId(netlist, letter) {
  var L = String(letter || "X").toUpperCase().charAt(0);
  var re = new RegExp("\\b" + L + "(\\d+)\\b", "gi");
  var max = 0;
  var m;
  while ((m = re.exec(netlist)) !== null) {
    var n = parseInt(m[1], 10);
    if (!isNaN(n) && n > max) max = n;
  }
  return L + (max + 1);
}

export function inferSpiceDeviceLetter(compType, payload) {
  var pl0 = String(payload || "").trim();
  if (/^\.subckt\b/i.test(pl0)) return "X";
  var ct = String(compType || "").toUpperCase();
  var pl = String(payload || "").toUpperCase();
  if (ct.indexOf("MOS") >= 0 || pl.indexOf("NMOS") >= 0 || pl.indexOf("PMOS") >= 0) return "M";
  if (ct.indexOf("BJT") >= 0 || ct.indexOf("NPN") >= 0 || ct.indexOf("PNP") >= 0) return "Q";
  if (ct.indexOf("JFET") >= 0 || pl.indexOf("NJF") >= 0 || pl.indexOf("PJF") >= 0)
    return "J";
  if (ct.indexOf("DIODE") >= 0 || ct === "D" || ct.indexOf("LED") >= 0 || ct.indexOf("SCHOTTKY") >= 0) return "D";
  if (ct.indexOf("SUB") >= 0 || pl.indexOf(".SUBCKT") >= 0) return "X";
  if (ct.indexOf("RES") >= 0 || ct === "R") return "R";
  if (ct.indexOf("CAP") >= 0 || ct === "C") return "C";
  if (ct.indexOf("IND") >= 0 || ct === "L") return "L";
  return "X";
}

/** Node tokens for instance line: semantic (catalog) vs generic n1/n2. */
function instanceNodeTokens(letter, row, semantic) {
  var pm = row && row.pin_map;
  if (semantic && pm && typeof pm === "object" && !Array.isArray(pm)) {
    var keys = Object.keys(pm).filter(function (k) {
      return pm[k] != null && !isNaN(Number(pm[k]));
    });
    if (keys.length) {
      keys.sort(function (a, b) {
        return Number(pm[a]) - Number(pm[b]);
      });
      return keys.join(" ");
    }
  }
  if (!semantic) {
    if (letter === "M") return "n1 n2 n3 0";
    if (letter === "Q" || letter === "J") return "n1 n2 n3";
    if (letter === "D") return "n1 n2";
    if (letter === "R" || letter === "C" || letter === "L") return "n1 n2";
    return "n1 n2 n3";
  }
  if (letter === "M") return "drain gate source body";
  if (letter === "Q") return "collector base emitter";
  if (letter === "D") return "anode cathode";
  if (letter === "J") return "drain gate source";
  if (letter === "R" || letter === "C" || letter === "L") return "n1 n2";
  return "n1 n2 n3";
}

function normalizeModelBlock(partNumber, compType, spicePayload) {
  var pn = String(partNumber || "").trim();
  var payload = String(spicePayload || "").trim();
  if (!payload) return "";
  if (/^\.model\b/i.test(payload)) return payload;
  if (/^\.subckt\b/i.test(payload)) return payload;
  var ct = String(compType || "").toUpperCase();
  var pl = payload.toUpperCase();
  var dev = "NMOS";
  if (ct.indexOf("PMOS") >= 0 || pl.indexOf("PMOS") >= 0) dev = "PMOS";
  else if (ct.indexOf("MOS") >= 0 || pl.indexOf("NMOS") >= 0) dev = "NMOS";
  else if (ct.indexOf("NPN") >= 0 || pl.indexOf("NPN") >= 0) dev = "NPN";
  else if (ct.indexOf("PNP") >= 0 || pl.indexOf("PNP") >= 0) dev = "PNP";
  else if (ct.indexOf("NJF") >= 0 || pl.indexOf("NJF") >= 0) dev = "NJF";
  else if (ct.indexOf("PJF") >= 0 || pl.indexOf("PJF") >= 0) dev = "PJF";
  else if (ct.indexOf("DIODE") >= 0 || ct.indexOf("LED") >= 0 || ct.indexOf("D") === 0) dev = "D";
  if (dev === "D" || dev === "NPN" || dev === "PNP" || dev === "NMOS" || dev === "PMOS" || dev === "NJF" || dev === "PJF") {
    var inner = payload;
    if (!inner.startsWith("(")) inner = "(" + inner + ")";
    return ".model " + pn + " " + dev + inner;
  }
  return ".model " + pn + " " + payload;
}

/**
 * @param {string} netlist
 * @param {object} row — ComponentCatalogRow-shaped
 * @param {{ semanticNodes?: boolean }} [opts] — default semantic true (D5EX-88C preview + insert parity)
 * @returns {{ instanceLine: string, modelBlock: string }}
 */
function buildInsertBlockCore(netlist, row, opts) {
  opts = opts || {};
  var semantic = opts.semanticNodes !== false;
  var pn = String(row.part_number || "").trim();
  var ct = String(row.comp_type || "");
  var payload = String(row.spice_payload || "").trim();
  var letter = inferSpiceDeviceLetter(ct, payload);
  var id = nextDeviceId(netlist, letter);
  var modelBlock = "";
  var instanceLine = "";
  var nodes = instanceNodeTokens(letter, row, semantic);
  if (letter === "M") {
    var np = nodes.trim().split(/\s+/).filter(Boolean);
    if (np.length === 3) nodes = nodes + " 0";
  }

  if (/^\.subckt\b/i.test(payload)) {
    instanceLine = id + " " + nodes + " " + pn;
    if (!netHasSubckt(netlist, pn)) modelBlock = payload;
  } else if (letter === "M") {
    instanceLine = id + " " + nodes + " " + pn + " W=10u L=1u";
    if (!netHasModelForPart(netlist, pn)) modelBlock = normalizeModelBlock(pn, ct, payload);
  } else if (letter === "Q") {
    instanceLine = id + " " + nodes + " " + pn;
    if (!netHasModelForPart(netlist, pn)) modelBlock = normalizeModelBlock(pn, ct, payload);
  } else if (letter === "J") {
    instanceLine = id + " " + nodes + " " + pn;
    if (!netHasModelForPart(netlist, pn)) modelBlock = normalizeModelBlock(pn, ct, payload);
  } else if (letter === "D") {
    instanceLine = id + " " + nodes + " " + pn;
    if (!netHasModelForPart(netlist, pn)) modelBlock = normalizeModelBlock(pn, ct, payload);
  } else if (letter === "R") {
    instanceLine = id + " " + nodes + " 1k";
  } else if (letter === "C") {
    instanceLine = id + " " + nodes + " 100n";
  } else if (letter === "L") {
    instanceLine = id + " " + nodes + " 1m";
  } else {
    instanceLine = id + " " + nodes + " " + pn;
    if (payload && !netHasModelForPart(netlist, pn) && !/^\.subckt/i.test(payload))
      modelBlock = normalizeModelBlock(pn, ct, payload);
  }

  return { instanceLine: instanceLine, modelBlock: modelBlock };
}

/**
 * @param {string} netlist
 * @param {object} row — ComponentCatalogRow-shaped
 * @returns {{ instanceLine: string, modelBlock: string, prefix: string, instId: string }}
 */
export function generateSpiceForPart(netlist, row) {
  var blk = buildInsertBlockCore(netlist, row, { semanticNodes: true });
  var m = /^(\S+)/.exec(String(blk.instanceLine || ""));
  var id = m ? m[1] : "";
  var letter = id ? String(id).charAt(0).toUpperCase() : inferSpiceDeviceLetter(row.comp_type, row.spice_payload);
  return {
    instanceLine: blk.instanceLine,
    modelBlock: blk.modelBlock,
    prefix: letter,
    instId: id,
  };
}

/**
 * @param {string} netlist
 * @param {object} row — ComponentCatalogRow-shaped
 * @returns {{ instanceLine: string, modelBlock: string }}
 */
export function buildInsertBlock(netlist, row) {
  return buildInsertBlockCore(netlist, row, { semanticNodes: true });
}

/**
 * Replace the trailing partial token on the current line with replacement text.
 * @param {string} fullText
 * @param {number} cursorPos
 * @param {string} replacement — e.g. full model name + " W=10u L=1u" for M
 */
export function replaceWordAtCursor(fullText, cursorPos, replacement) {
  var before = fullText.slice(0, cursorPos);
  var after = fullText.slice(cursorPos);
  var wm = before.match(/[.\w]+$/);
  if (!wm) {
    return { text: fullText.slice(0, cursorPos) + replacement + after, newPos: cursorPos + replacement.length };
  }
  var start = cursorPos - wm[0].length;
  var nw = fullText.slice(0, start) + replacement + after;
  return { text: nw, newPos: start + replacement.length };
}

/** Insert a single line before lineIndex0 (0-based). */
export function insertSingleLineAtLine(fullText, lineIndex0, line) {
  var lines = fullText.split("\n");
  var L = String(line || "").trim();
  if (!L) return fullText;
  lines.splice(Math.max(0, lineIndex0), 0, L);
  return lines.join("\n");
}

/** Insert block after a given 0-based line index (insert before that line). */
export function insertBlockAtLine(fullText, lineIndex0, instanceLine, modelBlock) {
  var lines = fullText.split("\n");
  var block = [instanceLine];
  if (modelBlock) {
    var mb = modelBlock.split("\n").filter(function (l) {
      return l.trim();
    });
    block = block.concat(mb);
  }
  lines.splice(lineIndex0, 0, block.join("\n"));
  return lines.join("\n");
}

/** Append model text before `.end` if present; otherwise append at EOF. */
export function appendModelsBeforeEnd(netlist, modelBlock) {
  if (!modelBlock || !String(modelBlock).trim()) return netlist;
  var mb = String(modelBlock).trim();
  var lines = netlist.split("\n");
  var endIdx = -1;
  for (var i = 0; i < lines.length; i++) {
    if (/^\s*\.end\s*$/i.test(lines[i])) endIdx = i;
  }
  if (endIdx >= 0) {
    lines.splice(endIdx, 0, mb);
    return lines.join("\n");
  }
  return netlist + (netlist.endsWith("\n") ? "" : "\n") + mb + "\n";
}
