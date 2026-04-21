/** Cooley-Tukey radix-2 FFT with Hann window (real input). */
export function fftRealRadix2(samples) {
  var N = samples.length,
    n = 1;
  while (n < N) n <<= 1;
  var re = new Float64Array(n),
    im = new Float64Array(n);
  for (var i = 0; i < N; i++)
    re[i] = samples[i] * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / Math.max(N - 1, 1)));
  for (var i = 1, j = 0; i < n; i++) {
    var bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      var t = re[i];
      re[i] = re[j];
      re[j] = t;
    }
  }
  for (var len = 2; len <= n; len <<= 1) {
    var ang = (-2 * Math.PI) / len,
      wr = Math.cos(ang),
      wi = Math.sin(ang);
    for (var i = 0; i < n; i += len) {
      var cr = 1,
        ci = 0,
        hh = len >> 1;
      for (var k = 0; k < hh; k++) {
        var ur = re[i + k],
          ui = im[i + k];
        var vr = re[i + k + hh] * cr - im[i + k + hh] * ci,
          vi = re[i + k + hh] * ci + im[i + k + hh] * cr;
        re[i + k] = ur + vr;
        im[i + k] = ui + vi;
        re[i + k + hh] = ur - vr;
        im[i + k + hh] = ui - vi;
        var nr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = nr;
      }
    }
  }
  return { re: re, im: im, n: n };
}

export function computeViewportMeasurements(xs, ys, xMin, xMax) {
  var pts = [],
    ts = [];
  for (var i = 0; i < xs.length; i++)
    if (xs[i] >= xMin && xs[i] <= xMax && isFinite(ys[i])) {
      pts.push(ys[i]);
      ts.push(xs[i]);
    }
  if (pts.length < 4) return null;
  var vmax = -Infinity,
    vmin = Infinity,
    sum = 0,
    sum2 = 0;
  for (var i = 0; i < pts.length; i++) {
    if (pts[i] > vmax) vmax = pts[i];
    if (pts[i] < vmin) vmin = pts[i];
    sum += pts[i];
    sum2 += pts[i] * pts[i];
  }
  var mean = sum / pts.length,
    vrms = Math.sqrt(sum2 / pts.length),
    vpp = vmax - vmin;
  var cross = 0;
  for (var i = 1; i < pts.length; i++) if ((pts[i - 1] - mean) * (pts[i] - mean) < 0) cross++;
  var tspan = (ts.length > 1 ? ts[ts.length - 1] - ts[0] : 1) || 1;
  var freq = cross >= 2 ? cross / 2 / tspan : null,
    period = freq ? 1 / freq : null;
  var lo10 = vmin + 0.1 * vpp,
    hi90 = vmin + 0.9 * vpp,
    riseT = null,
    fallT = null;
  for (var i = 1; i < pts.length && (riseT == null || fallT == null); i++) {
    if (riseT == null && pts[i - 1] <= lo10 && pts[i] >= lo10) {
      var tlo = ts[i - 1] + ((ts[i] - ts[i - 1]) * (lo10 - pts[i - 1])) / (pts[i] - pts[i - 1] || 1);
      for (var j = i; j < pts.length; j++)
        if (pts[j] >= hi90) {
          riseT =
            ts[j - 1] +
            ((ts[j] - ts[j - 1]) * (hi90 - pts[j - 1])) / (pts[j] - pts[j - 1] || 1) -
            tlo;
          break;
        }
    }
    if (fallT == null && pts[i - 1] >= hi90 && pts[i] <= hi90) {
      var thi = ts[i - 1] + ((ts[i] - ts[i - 1]) * (hi90 - pts[i - 1])) / (pts[i] - pts[i - 1] || 1);
      for (var j = i; j < pts.length; j++)
        if (pts[j] <= lo10) {
          fallT =
            ts[j - 1] +
            ((ts[j] - ts[j - 1]) * (lo10 - pts[j - 1])) / (pts[j] - pts[j - 1] || 1) -
            thi;
          break;
        }
    }
  }
  var above = 0;
  for (var i = 0; i < pts.length; i++) if (pts[i] >= mean) above++;
  return {
    vmax: vmax,
    vmin: vmin,
    vpp: vpp,
    vrms: vrms,
    mean: mean,
    freq: freq,
    period: period,
    riseT: riseT,
    fallT: fallT,
    duty: (above / pts.length) * 100,
  };
}
