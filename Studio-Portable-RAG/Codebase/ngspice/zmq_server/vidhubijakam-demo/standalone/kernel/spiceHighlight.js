export function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Class-based spans so the numeric highlighter cannot match hex digits inside style="color:#…". */
export function hlS(c) {
  return c
    .split("\n")
    .map(function (L) {
      if (/^\s*[*;]/.test(L)) return '<span class="vb-hl-com">' + esc(L) + "</span>";
      var o = esc(L);
      o = o.replace(/^(\.[a-zA-Z]+)/, '<span class="vb-hl-dir">$1</span>');
      o = o.replace(/\b(NPN|PNP|NMOS|PMOS|VDMOS|NJF|PJF)\b/g, '<span class="vb-hl-typ">$1</span>');
      o = o.replace(/\b(DC|AC|SIN|PULSE|PWL|EXP|SFFM)\b/g, '<span class="vb-hl-src">$1</span>');
      o = o.replace(/\b(\d+\.?\d*[fpnumkMGT]?[A-Za-z]*)\b/g, '<span class="vb-hl-num">$1</span>');
      o = o.replace(/\b([A-Z][A-Z0-9_]*)=/g, '<span class="vb-hl-par">$1</span>=');
      return o;
    })
    .join("\n");
}

export const VB_HL_CSS =
  ".vb-hl-com{color:#008000;font-style:italic}" +
  ".vb-hl-dir{color:#0000FF;font-weight:bold}" +
  ".vb-hl-typ{color:#800080;font-weight:bold}" +
  ".vb-hl-src{color:#FF8000}" +
  ".vb-hl-num{color:#FF0000}" +
  ".vb-hl-par{color:#808000}" +
  ".vb-hl-ai{background:#E3F2FD;font-style:italic;color:#1565C0;display:inline-block;width:100%}";
