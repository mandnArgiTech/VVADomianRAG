/** Vite dev: same-origin `/api` (proxy). Production/preview: point UI at your engine host. */
export function defaultApiBaseForDemo() {
  try {
    if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV) return "";
  } catch (_e) {}
  return "http://localhost:8000";
}

/** Injected at build/dev time from repo-root `.env` (`DEEP_SEEK_API_KEY`) via Vite `define`. */
export function defaultDeepSeekKeyFromEnv() {
  try {
    if (
      typeof import.meta !== "undefined" &&
      import.meta.env &&
      import.meta.env.VITE_DEFAULT_DEEP_SEEK_API_KEY
    )
      return String(import.meta.env.VITE_DEFAULT_DEEP_SEEK_API_KEY);
  } catch (_e) {}
  return "";
}

/** Trim and strip trailing slashes so `base + "/api/..."` never becomes `//api`. */
export function normalizeApiBase(b) {
  return String(b == null ? "" : b)
    .trim()
    .replace(/\/+$/, "");
}

/** One retry after short delay when the engine boot gate returns 503. */
export function fetchOnce503Retry(url, init) {
  return fetch(url, init).then(function (r) {
    if (r.status !== 503) return r;
    return new Promise(function (resolve) {
      setTimeout(function () {
        resolve(fetch(url, init));
      }, 700);
    });
  });
}
