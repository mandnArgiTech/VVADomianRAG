export function fe(v, u) {
  u = u || "";
  if (v == null || !isFinite(v)) return "\u2014";
  var a = Math.abs(v),
    s = v < 0 ? "-" : "";
  if (a === 0) return "0 " + u;
  if (a >= 1e9) return s + (a / 1e9).toPrecision(4) + " G" + u;
  if (a >= 1e6) return s + (a / 1e6).toPrecision(4) + " M" + u;
  if (a >= 1e3) return s + (a / 1e3).toPrecision(4) + " k" + u;
  if (a >= 1) return s + a.toPrecision(4) + " " + u;
  if (a >= 1e-3) return s + (a * 1e3).toPrecision(4) + " m" + u;
  if (a >= 1e-6) return s + (a * 1e6).toPrecision(4) + " \u00b5" + u;
  if (a >= 1e-9) return s + (a * 1e9).toPrecision(4) + " n" + u;
  return v.toExponential(3) + " " + u;
}
