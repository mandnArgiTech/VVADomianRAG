export function inferAnalysisFromNetlistLower(cl) {
  var at = "op";
  if (cl.indexOf(".ac ") >= 0) at = "ac";
  else if (cl.indexOf(".tran ") >= 0) at = "tran";
  else if (cl.indexOf(".dc ") >= 0) at = "dc";
  return at;
}

/** First row that can populate the editor (embedded netlist or `.cir` path). */
export function firstLoadableCatalogItem(items) {
  for (var i = 0; i < (items || []).length; i++) {
    var it = items[i];
    if (!it) continue;
    if (it.net && String(it.net).trim()) return it;
    if (it.p && String(it.p).trim()) return it;
  }
  return null;
}
