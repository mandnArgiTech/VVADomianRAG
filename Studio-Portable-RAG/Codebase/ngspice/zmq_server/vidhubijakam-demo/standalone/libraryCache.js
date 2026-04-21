/**
 * Boot-time component catalog cache for VidhuBijakam demo (D5EX-88A).
 * Uses GET /api/components/count-by-type and POST /api/components/search.
 */

function normalizeApiBase(b) {
  return String(b || "")
    .trim()
    .replace(/\/+$/, "");
}

/** Single delayed retry when boot middleware returns 503. */
async function fetch503Retry(url, init) {
  var r = await fetch(url, init);
  if (r.status !== 503) return r;
  await new Promise(function (res) {
    setTimeout(res, 700);
  });
  return fetch(url, init);
}

var MAX_TYPES_TO_PREFETCH = 22;
var TOP_PER_TYPE = 20;
var SEARCH_CONCURRENCY = 5;

function emptyCache() {
  return {
    ready: false,
    total: 0,
    types: [],
    topParts: {},
    flatIndex: [],
    error: null,
  };
}

/**
 * Run async tasks with limited concurrency.
 * @param {Array<T>} items
 * @param {number} limit
 * @param {(item: T) => Promise<void>} worker
 */
async function runPool(items, limit, worker) {
  var i = 0;
  var runners = new Array(Math.min(limit, items.length)).fill(0).map(function () {
    return (async function () {
      while (i < items.length) {
        var idx = i++;
        await worker(items[idx]);
      }
    })();
  });
  await Promise.all(runners);
}

/** @param {string} apiBase */
export async function initLibraryCache(apiBase) {
  var cache = emptyCache();
  var root = normalizeApiBase(apiBase);
  try {
    var r = await fetch503Retry(root + "/api/components/count-by-type", undefined);
    if (!r.ok) throw new Error("HTTP " + r.status);
    var data;
    try {
      data = await r.json();
    } catch (_json) {
      throw new Error("Invalid JSON from count-by-type");
    }
    var rows = data.by_type || [];
    cache.total = typeof data.total === "number" ? data.total : 0;
    cache.types = rows
      .map(function (t) {
        return { type: String(t.comp_type || t.type || "").trim(), count: Number(t.count) || 0 };
      })
      .filter(function (t) {
        return t.type;
      })
      .sort(function (a, b) {
        return b.count - a.count || a.type.localeCompare(b.type);
      });

    var slice = cache.types.slice(0, MAX_TYPES_TO_PREFETCH);

    await runPool(slice, SEARCH_CONCURRENCY, async function (trow) {
      var t = trow.type;
      try {
        var sr = await fetch(root + "/api/components/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text_query: "", comp_type: t, limit: TOP_PER_TYPE }),
        });
        var sd = { results: [] };
        if (sr.ok) {
          try {
            sd = await sr.json();
          } catch (_je) {
            sd = { results: [] };
          }
        }
        cache.topParts[t] = sd.results || [];
      } catch (_e) {
        cache.topParts[t] = [];
      }
    });

    Object.keys(cache.topParts).forEach(function (type) {
      (cache.topParts[type] || []).forEach(function (part, idx) {
        cache.flatIndex.push({
          pnUpper: String(part.part_number || "")
            .toUpperCase()
            .trim(),
          type: type,
          idx: idx,
          descLower: String(part.description || "").toLowerCase(),
          mfrLower: String(part.manufacturer || "").toLowerCase(),
        });
      });
    });

    cache.ready = true;
  } catch (e) {
    cache.error = e && e.message ? String(e.message) : "fetch failed";
    cache.ready = false;
  }
  return cache;
}

/**
 * @param {ReturnType<typeof emptyCache>} cache
 * @param {string} query
 * @param {{ limit?: number }} [opts]
 */
export function searchLocal(cache, query, opts) {
  opts = opts || {};
  var lim = opts.limit != null ? opts.limit : 15;
  if (!cache || !cache.ready || !query || String(query).length < 2) return [];
  var q = String(query).trim();
  var qu = q.toUpperCase();
  var ql = q.toLowerCase();
  var seen = {};
  var out = [];
  for (var i = 0; i < cache.flatIndex.length; i++) {
    var e = cache.flatIndex[i];
    if (!e.pnUpper) continue;
    if (
      e.pnUpper.indexOf(qu) < 0 &&
      e.descLower.indexOf(ql) < 0 &&
      e.mfrLower.indexOf(ql) < 0
    )
      continue;
    var row = (cache.topParts[e.type] || [])[e.idx];
    if (!row || seen[row.part_number]) continue;
    seen[row.part_number] = 1;
    out.push(row);
    if (out.length >= lim) break;
  }
  return out;
}

export async function searchRemote(apiBase, query, compType, limit) {
  var root = normalizeApiBase(apiBase);
  try {
    var r = await fetch(root + "/api/components/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text_query: query || "",
        comp_type: compType || "",
        limit: limit || 30,
      }),
    });
    if (!r.ok) return [];
    var d = await r.json();
    return d.results || [];
  } catch (_e) {
    return [];
  }
}

export async function getPartDetail(apiBase, partNumber) {
  var root = normalizeApiBase(apiBase);
  var enc = encodeURIComponent(String(partNumber || "").trim());
  if (!enc) return null;
  try {
    var r = await fetch(root + "/api/components/" + enc);
    if (!r.ok) return null;
    return await r.json();
  } catch (_e) {
    return null;
  }
}

export function getTypes(cache) {
  return (cache && cache.types) || [];
}

export function getTopParts(cache, type) {
  if (!cache || !cache.topParts) return [];
  return cache.topParts[type] || [];
}

/** Summarize catalog for AI prompt (D5EX-88). */
export function buildLibraryContextForAI(cache, opts) {
  opts = opts || {};
  if (!cache || !cache.ready) return "";
  var maxTypes = opts.maxTypes != null ? opts.maxTypes : 8;
  var perType = opts.perType != null ? opts.perType : 6;
  var lines = [];
  lines.push("Component library (use these real part_numbers when applicable):");
  lines.push("Total catalog parts (approx): " + (cache.total || cache.flatIndex.length));
  var types = (cache.types || []).slice(0, maxTypes);
  for (var i = 0; i < types.length; i++) {
    var t = types[i].type;
    var parts = (cache.topParts[t] || []).slice(0, perType);
    if (!parts.length) continue;
    var bits = parts.map(function (p) {
      var pn = p.part_number || "?";
      var d = (p.description || "").replace(/\s+/g, " ").slice(0, 80);
      return pn + (d ? " — " + d : "");
    });
    lines.push("- " + t + ": " + bits.join("; "));
  }
  lines.push(
    "Include .model / .subckt lines from the library spice_payload when you name a listed part. If no listed part fits, use a generic .model with a new name."
  );
  return lines.join("\n");
}
