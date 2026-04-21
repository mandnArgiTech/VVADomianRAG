var STORAGE_KEY = "vb-kernel-user-circuits-v1";
var MAX_ENTRIES = 200;

function sanitizeEntry(x) {
  if (!x || typeof x !== "object") return null;
  if (typeof x.id !== "string" || typeof x.name !== "string" || typeof x.net !== "string") return null;
  var an = String(x.an || "op")
    .trim()
    .toLowerCase();
  if (!/^(op|ac|tran|dc)$/.test(an)) an = "op";
  return {
    id: x.id,
    name: x.name,
    net: x.net,
    an: an,
    savedAt: typeof x.savedAt === "number" ? x.savedAt : Date.now(),
  };
}

export function readUserCircuits() {
  try {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    var j = JSON.parse(raw);
    if (!Array.isArray(j)) return [];
    var out = [];
    for (var i = 0; i < j.length; i++) {
      var s = sanitizeEntry(j[i]);
      if (s) out.push(s);
    }
    return out;
  } catch {
    return [];
  }
}

function writeRaw(list) {
  var trimmed = list.slice(-MAX_ENTRIES);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
}

/**
 * Insert or replace by circuit name (same name updates in place).
 * @returns {{ id: string, name: string, net: string, an: string, savedAt: number }}
 */
export function upsertUserCircuit(name, net, an) {
  var list = readUserCircuits();
  var trimmedName = String(name || "")
    .trim()
    .replace(/\s+/g, " ");
  if (!trimmedName) trimmedName = "circuit";
  var anUse = String(an || "op")
    .trim()
    .toLowerCase();
  if (!/^(op|ac|tran|dc)$/.test(anUse)) anUse = "op";
  var ix = list.findIndex(function (x) {
    return x.name === trimmedName;
  });
  var id = ix >= 0 ? list[ix].id : "uc_" + Date.now() + "_" + Math.random().toString(36).slice(2, 10);
  var entry = { id: id, name: trimmedName, net: net, an: anUse, savedAt: Date.now() };
  if (ix >= 0) list[ix] = entry;
  else list.push(entry);
  writeRaw(list);
  return entry;
}
