/**
 * Chunk Inspector: browse files, load Chroma chunks, highlight by exact match (normalized newlines).
 */
(function () {
  /* Soft tints on white — readable with Courier New body text */
  const CHUNK_TYPE_COLORS = {
    device_load_function: 'rgba(59, 130, 246, 0.16)',
    matrix_solver_function: 'rgba(16, 185, 129, 0.16)',
    device_setup_function: 'rgba(124, 58, 237, 0.14)',
    core_constant: 'rgba(217, 119, 6, 0.16)',
    file_preamble: 'rgba(148, 163, 184, 0.28)',
    preproc_def: 'rgba(14, 165, 233, 0.14)',
    preproc_function_def: 'rgba(6, 182, 212, 0.14)',
    default: 'rgba(71, 85, 105, 0.14)',
  };

  const $ = (id) => document.getElementById(id);

  let chunkBrowseRel = '';
  let chunkSplitH = null;
  let chunkSplitV = null;
  /** @type {{ chunks: any[], path: string, absSource: string, rawNorm: string } | null} */
  let chunkState = null;
  /** Full catalog from Connect DB (chunk_id, rel_path, metadata, …) */
  let dbCatalogChunks = null;
  /** When true, file open does not replace the ingested-chunks list (catalog stays). */
  let catalogLocked = false;
  let selectedChunkId = null;
  let metaDrag = { on: false, sx: 0, sy: 0, elx: 0, ely: 0 };

  function normalizeNewlines(s) {
    if (!s) return '';
    return String(s).replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function attrEscape(s) {
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  }

  function colorForType(t) {
    const k = (t && String(t)) || '';
    return CHUNK_TYPE_COLORS[k] || CHUNK_TYPE_COLORS.default;
  }

  function chunkSortKey(c) {
    const m = c.metadata || {};
    const idx = parseInt(String(m.chunk_index || '0'), 10);
    return Number.isFinite(idx) ? idx : 0;
  }

  /**
   * Build non-overlapping highlight intervals in normalized text.
   */
  function buildIntervals(displayNorm, chunks) {
    const ordered = [...chunks].sort((a, b) => chunkSortKey(a) - chunkSortKey(b));
    const used = [];
    const cursors = new Map();

    for (const c of ordered) {
      const rawText = c.text || '';
      const normChunk = normalizeNewlines(rawText);
      if (!normChunk) continue;

      let start = displayNorm.indexOf(normChunk, cursors.get(normChunk) || 0);
      if (start < 0) start = displayNorm.indexOf(normChunk, 0);
      if (start < 0) continue;

      const end = start + normChunk.length;
      let overlap = false;
      for (const u of used) {
        if (!(end <= u.start || start >= u.end)) {
          overlap = true;
          break;
        }
      }
      if (overlap) continue;

      used.push({
        start,
        end,
        chunkId: c.chunk_id,
        style: colorForType((c.metadata || {}).chunk_type),
        meta: c,
      });
      cursors.set(normChunk, start + 1);
    }
    used.sort((a, b) => a.start - b.start);
    return used;
  }

  function buildHighlightedHtml(displayNorm, intervals) {
    let pos = 0;
    const parts = [];
    for (const iv of intervals) {
      if (iv.start > pos) parts.push(escapeHtml(displayNorm.slice(pos, iv.start)));
      const inner = escapeHtml(displayNorm.slice(iv.start, iv.end));
      const cid = attrEscape(iv.chunkId);
      parts.push(
        '<mark class="chunk-mark" data-chunk-id="' +
          cid +
          '" style="background:' +
          iv.style +
          ';">' +
          inner +
          '</mark>'
      );
      pos = iv.end;
    }
    if (pos < displayNorm.length) parts.push(escapeHtml(displayNorm.slice(pos)));
    return parts.join('');
  }

  function showMetaForChunk(chunkId, scrollMark) {
    let c = chunkState ? chunkState.chunks.find((x) => x.chunk_id === chunkId) : null;
    if (!c && dbCatalogChunks) {
      c = dbCatalogChunks.find((x) => x.chunk_id === chunkId);
    }
    if (!c) return;

    selectedChunkId = chunkId;
    document.querySelectorAll('#chunkVisualizerCode mark.chunk-mark').forEach((el) => {
      el.classList.toggle('chunk-mark-selected', el.getAttribute('data-chunk-id') === chunkId);
    });
    document.querySelectorAll('.chunk-list-row').forEach((row) => {
      row.classList.toggle('chunk-list-selected', row.getAttribute('data-chunk-id') === chunkId);
    });

    const m = c.metadata || {};
    const abs = c.abs_source || m.source || '—';
    const rel = c.rel_path || '—';
    const lines = [
      ['chunk_name', m.chunk_name || '—'],
      ['chunk_type', m.chunk_type || '—'],
      ['collection', c.collection || '—'],
      ['chunk_index', m.chunk_index || '—'],
      ['source (abs)', abs],
      ['rel_path', rel],
      ['device_family', m.device_family || '—'],
      ['concepts', m.concepts || '—'],
      ['source_type', m.source_type || '—'],
    ];
    const body = $('chunkMetaFloatBody');
    if (body) {
      body.innerHTML = lines
        .map(
          ([k, v]) =>
            '<div class="mb-2"><span class="text-slate-500 text-[10px] uppercase">' +
            escapeHtml(k) +
            '</span><div class="text-xs font-mono text-slate-200 break-all">' +
            escapeHtml(String(v)) +
            '</div></div>'
        )
        .join('');
    }
    const panel = $('chunkMetaFloat');
    if (panel) {
      panel.classList.remove('hidden');
      if (!panel.style.left) {
        panel.style.right = '24px';
        panel.style.bottom = '24px';
        panel.style.left = 'auto';
        panel.style.top = 'auto';
      }
    }

    if (scrollMark) {
      let mark = null;
      document.querySelectorAll('#chunkVisualizerCode mark.chunk-mark').forEach((el) => {
        if (el.getAttribute('data-chunk-id') === chunkId) mark = el;
      });
      if (mark) {
        requestAnimationFrame(() => scrollChunkMarkIntoView(mark));
      }
    }
  }

  function chunkSourceBaseParam() {
    const el = $('chunkSourceBase');
    return el && el.value.trim() ? el.value.trim() : '';
  }

  function normalizeRelPath(p) {
    return String(p || '')
      .trim()
      .replace(/\\/g, '/')
      .replace(/^\/+/, '');
  }

  /**
   * Scroll only #chunkVizScroll so wheel / scrollIntoView does not move the left column or page.
   */
  function scrollChunkMarkIntoView(mark) {
    const sc = $('chunkVizScroll');
    if (!mark || !sc) return;
    const m = mark.getBoundingClientRect();
    const s = sc.getBoundingClientRect();
    const delta = m.top + m.height / 2 - (s.top + s.height / 2);
    sc.scrollTop += delta;
  }

  /**
   * Point Code explorer at the folder containing `relPath` and select the file row.
   */
  async function syncExplorerToOpenedFile(relPath) {
    const norm = normalizeRelPath(relPath);
    if (!norm) return;
    const parts = norm.split('/').filter(Boolean);
    if (!parts.length) return;
    const parent = parts.length > 1 ? parts.slice(0, -1).join('/') : '';
    chunkBrowseRel = parent;
    await loadChunkBrowse();
    const sel = $('chunkBrowseList');
    if (!sel) return;
    for (let i = 0; i < sel.options.length; i++) {
      const o = sel.options[i];
      const v = normalizeRelPath(o.value);
      if (o.dataset.type === 'file' && v === norm) {
        sel.selectedIndex = i;
        sel.focus();
        break;
      }
    }
  }

  async function loadChunkBrowse() {
    const q = new URLSearchParams({ path: chunkBrowseRel });
    const sb = chunkSourceBaseParam();
    if (sb) q.set('source_base', sb);
    const r = await fetch('/api/browse?' + q);
    const pathEl = $('chunkBrowsePath');
    if (!r.ok) {
      const t = await r.text().catch(() => r.statusText);
      if (pathEl) pathEl.textContent = 'browse error: HTTP ' + r.status;
      const sel = $('chunkBrowseList');
      if (sel) {
        sel.innerHTML = '';
        const opt = document.createElement('option');
        opt.disabled = true;
        opt.textContent = (t || 'request failed').slice(0, 200);
        sel.appendChild(opt);
      }
      return;
    }
    let j = { root: '', path: '', entries: [] };
    try {
      j = await r.json();
    } catch (e) {
      if (pathEl) pathEl.textContent = 'browse error: invalid JSON';
      return;
    }
    if (pathEl) pathEl.textContent = j.root + (chunkBrowseRel ? '/' + chunkBrowseRel : '');
    const sel = $('chunkBrowseList');
    if (!sel) return;
    sel.innerHTML = '';
    const list = j.entries || [];
    for (const e of list) {
      const opt = document.createElement('option');
      opt.value = e.path;
      opt.textContent = (e.type === 'directory' ? '📁 ' : '📄 ') + e.name;
      opt.dataset.type = e.type;
      sel.appendChild(opt);
    }
    if (list.length === 0) {
      const opt = document.createElement('option');
      opt.disabled = true;
      opt.textContent = '(empty folder)';
      sel.appendChild(opt);
    }
  }

  const CATALOG_PAGE_LIMIT = 800;

  function buildCatalogRowElement(c) {
    const m = c.metadata || {};
    const row = document.createElement('div');
    row.className =
      'chunk-list-row text-xs font-mono border-b border-slate-800/80 px-2 py-1.5 cursor-pointer hover:bg-slate-800/50';
    row.setAttribute('data-chunk-id', c.chunk_id);
    const idx = m.chunk_index != null && m.chunk_index !== '' ? String(m.chunk_index) : '—';
    const preview = (c.text || '').slice(0, 72).replace(/\s+/g, ' ');
    const relShow = (c.rel_path || '(no rel_path — adjust Source base)').slice(0, 120);
    row.innerHTML =
      '<div class="text-violet-300/90 truncate">' +
      escapeHtml(m.chunk_name || c.chunk_id) +
      '</div>' +
      '<div class="text-slate-500 truncate">' +
      escapeHtml(String(m.collection || c.collection || '')) +
      ' · idx ' +
      escapeHtml(idx) +
      ' · ' +
      escapeHtml(m.chunk_type || '') +
      '</div>' +
      '<div class="text-cyan-600/70 truncate" title="' +
      attrEscape(relShow) +
      '">' +
      escapeHtml(relShow) +
      '</div>' +
      '<div class="text-slate-600/80 truncate">' +
      escapeHtml(preview) +
      (c.text_truncated ? ' <span class="text-amber-400">…</span>' : '') +
      '</div>';
    row.addEventListener('click', () => {
      void onCatalogChunkClick(c);
    });
    return row;
  }

  function setCatalogProgress(loaded, total, label) {
    const wrap = $('chunkCatalogProgressWrap');
    const bar = $('chunkCatalogProgressBar');
    const lbl = $('chunkCatalogProgressLabel');
    const cnt = $('chunkCatalogProgressCounts');
    if (wrap) wrap.classList.remove('hidden');
    if (lbl && label != null) lbl.textContent = label;
    if (cnt) cnt.textContent = total > 0 ? loaded + ' / ' + total : loaded + ' / …';
    if (bar) {
      if (total > 0) bar.style.width = Math.min(100, (100 * loaded) / total) + '%';
      else bar.style.width = loaded > 0 ? '8%' : '0%';
    }
  }

  function hideCatalogProgress() {
    $('chunkCatalogProgressWrap')?.classList.add('hidden');
    const bar = $('chunkCatalogProgressBar');
    if (bar) bar.style.width = '0%';
  }

  /** Status / errors above the chunk list (does not scroll with rows). */
  function hideChunkCatalogBanner() {
    const b = $('chunkCatalogBanner');
    if (b) {
      b.classList.add('hidden');
      b.innerHTML = '';
    }
  }

  function showChunkCatalogBanner(html) {
    const b = $('chunkCatalogBanner');
    if (!b) return;
    b.innerHTML = html;
    b.classList.remove('hidden');
  }

  function appendCatalogChunkRow(c) {
    const wrap = $('chunkListInner');
    if (!wrap) return;
    wrap.appendChild(buildCatalogRowElement(c));
  }

  function renderDbCatalog(chunks, scanErrors) {
    const wrap = $('chunkListInner');
    if (!wrap) return;
    const errs = scanErrors && scanErrors.length ? scanErrors : [];
    if (!chunks || !chunks.length) {
      let banner =
        '<p class="text-slate-400 m-0">No rows in the catalog. If the DB has chunks, check the server log; the list API reports per-collection errors below.</p>';
      if (errs.length) {
        banner +=
          '<pre class="text-[10px] font-mono text-red-300/90 mt-2 mb-0 whitespace-pre-wrap border-t border-slate-800 pt-2">' +
          escapeHtml(errs.join('\n')) +
          '</pre>';
      }
      showChunkCatalogBanner(banner);
      wrap.innerHTML =
        '<p class="text-xs text-slate-600 p-2 m-0">No catalog rows. Connect DB after fixing errors, or open a file below.</p>';
      return;
    }
    hideChunkCatalogBanner();
    const sorted = [...chunks].sort((a, b) => {
      const ra = (a.rel_path || '').localeCompare(b.rel_path || '');
      if (ra !== 0) return ra;
      return chunkSortKey(a) - chunkSortKey(b);
    });
    wrap.innerHTML = '';
    for (const c of sorted) {
      wrap.appendChild(buildCatalogRowElement(c));
    }
  }

  function applyChunkPingBadge(badge, pingJ, catalogTotalLoaded) {
    if (!badge) return;
    const n = pingJ.collection_names && pingJ.collection_names.length;
    const cols = n ? n + ' collection(s)' : '0 collections';
    const model = pingJ.embedding_model_detected || '(unknown)';
    let prefix = '✓ ';
    let cls = 'text-emerald-400';
    if (!pingJ.exists) {
      prefix = '⚠ path missing — ';
      cls = 'text-red-300';
    } else if (!n) {
      prefix = '⚠ ';
      cls = 'text-amber-300';
    }
    badge.textContent =
      prefix + cols + ' · ' + model + ' · catalog ' + (catalogTotalLoaded != null ? catalogTotalLoaded : '—') + ' rows';
    badge.className = 'text-[10px] font-mono shrink-0 ' + cls;
  }

  async function onCatalogChunkClick(c) {
    const hintEl = $('chunkInspectorHint');
    const rel = (c.rel_path || '').trim();
    if (!rel) {
      if (hintEl) {
        hintEl.textContent =
          'This chunk has no rel_path under the current Source base. Set Source base to the folder that matches ingest metadata paths, then Connect DB again.';
      }
      showMetaForChunk(c.chunk_id, false);
      return;
    }
    if (!chunkState || chunkState.path !== rel) {
      await openChunkFile(rel);
    }
    showMetaForChunk(c.chunk_id, true);
  }

  async function connectChunkDatabase() {
    const badge = $('chunkDbPingBadge');
    const hintEl = $('chunkInspectorHint');
    const wrap = $('chunkListInner');
    const btn = $('chunkBtnConnectDb');
    if (badge) {
      badge.textContent = 'Connecting…';
      badge.className = 'text-[10px] font-mono text-slate-500 shrink-0';
    }
    if (hintEl) hintEl.textContent = '';
    hideChunkCatalogBanner();
    if (wrap) wrap.innerHTML = '';
    if (btn) btn.disabled = true;
    hideCatalogProgress();
    setCatalogProgress(0, 0, 'Preparing…');

    const dbEl = $('chunkInspectDbPath');
    const dbParam = dbEl && dbEl.value.trim() ? dbEl.value.trim() : '';
    const sb = chunkSourceBaseParam();
    const pingQ = new URLSearchParams();
    if (dbParam) pingQ.set('db_path', dbParam);

    function listUrl(off) {
      const q = new URLSearchParams();
      if (dbParam) q.set('db_path', dbParam);
      if (sb) q.set('source_base', sb);
      q.set('offset', String(off));
      q.set('page_limit', String(CATALOG_PAGE_LIMIT));
      return '/api/chunks/list?' + q;
    }

    let pingJ = {};
    const allErrors = [];
    try {
      const pingR = await fetch('/api/db/ping?' + pingQ);
      try {
        pingJ = await pingR.json();
      } catch (_) {}
      setCatalogProgress(0, 0, 'Loading first page…');
      const firstR = await fetch(listUrl(0));
      const firstJ = await firstR.json().catch(() => ({}));
      if (!firstR.ok) {
        const err =
          firstJ.detail != null
            ? typeof firstJ.detail === 'string'
              ? firstJ.detail
              : JSON.stringify(firstJ.detail)
            : firstJ.error || firstR.statusText;
        if (badge) {
          badge.textContent = 'List failed: ' + String(err).slice(0, 140);
          badge.className = 'text-[10px] font-mono text-red-300 shrink-0';
        }
        catalogLocked = false;
        dbCatalogChunks = null;
        renderDbCatalog([], [String(err)]);
        return;
      }

      const totalInDb = firstJ.total_in_db != null ? firstJ.total_in_db : 0;
      if (firstJ.scan_errors && firstJ.scan_errors.length) {
        allErrors.push.apply(allErrors, firstJ.scan_errors);
      }

      dbCatalogChunks = [];
      catalogLocked = true;
      hideChunkCatalogBanner();
      const page0 = firstJ.chunks || [];
      for (const c of page0) {
        dbCatalogChunks.push(c);
        appendCatalogChunkRow(c);
      }
      let nextOff = firstJ.next_offset != null ? firstJ.next_offset : page0.length;
      setCatalogProgress(nextOff, totalInDb, 'Loading catalog…');
      applyChunkPingBadge(badge, pingJ, nextOff);
      await new Promise((r) => requestAnimationFrame(r));

      let hasMore = firstJ.has_more === true;
      while (hasMore) {
        const r = await fetch(listUrl(nextOff));
        const j = await r.json().catch(() => ({}));
        if (!r.ok) {
          allErrors.push('page @' + nextOff + ': ' + (j.detail || r.statusText));
          break;
        }
        if (j.scan_errors && j.scan_errors.length) {
          allErrors.push.apply(allErrors, j.scan_errors);
        }
        const part = j.chunks || [];
        if (part.length === 0) {
          break;
        }
        for (const c of part) {
          dbCatalogChunks.push(c);
          appendCatalogChunkRow(c);
        }
        nextOff = j.next_offset != null ? j.next_offset : nextOff + part.length;
        setCatalogProgress(nextOff, totalInDb, 'Loading catalog…');
        applyChunkPingBadge(badge, pingJ, nextOff);
        await new Promise((r) => setTimeout(r, 0));
        hasMore = j.has_more === true;
      }

      setCatalogProgress(nextOff, totalInDb, 'Done');
      applyChunkPingBadge(badge, pingJ, nextOff);

      const counts = firstJ.collection_counts || {};
      const nColl = (firstJ.collections_order || []).length;
      if (hintEl) {
        const countStr = Object.keys(counts).length
          ? ' · Chroma counts: ' +
            Object.entries(counts)
              .map(([n, c]) => n + '=' + c)
              .join(', ')
          : '';
        let errStr = '';
        if (allErrors.length) {
          errStr = ' · Errors: ' + allErrors.slice(0, 3).join(' | ');
          if (allErrors.length > 3) errStr += ' …';
        }
        hintEl.textContent =
          'Catalog: ' +
          nextOff +
          ' row(s) in UI (total in DB ' +
          totalInDb +
          ', page size ' +
          CATALOG_PAGE_LIMIT +
          ').' +
          countStr +
          errStr;
      }
      if (dbCatalogChunks.length === 0 && allErrors.length) {
        renderDbCatalog([], allErrors);
      }
    } catch (e) {
      console.error(e);
      if (badge) {
        badge.textContent = 'Network error';
        badge.className = 'text-[10px] font-mono text-red-300 shrink-0';
      }
      catalogLocked = false;
      dbCatalogChunks = null;
    } finally {
      hideCatalogProgress();
      if (btn) btn.disabled = false;
    }
  }

  function renderChunkList(chunks, path) {
    const wrap = $('chunkListInner');
    if (!wrap) return;
    hideChunkCatalogBanner();
    if (!chunks.length) {
      wrap.innerHTML =
        '<p class="text-xs text-slate-500 p-2">' +
        (path
          ? 'No chunks for this file. Ingest with the same absolute path as shown in the status line (<code class="text-cyan-600/80">abs_source</code> from API must match Chroma metadata <code class="text-cyan-600/80">source</code>).'
          : 'Select a file in the explorer (double-click or Open file).') +
        '</p>';
      return;
    }
    wrap.innerHTML = '';
    for (const c of chunks) {
      const m = c.metadata || {};
      const row = document.createElement('div');
      row.className = 'chunk-list-row text-xs font-mono border-b border-slate-800/80 px-2 py-1.5';
      row.setAttribute('data-chunk-id', c.chunk_id);
      const truncated = (c.text || '').length >= 100000;
      const preview = (c.text || '').slice(0, 80).replace(/\s+/g, ' ');
      row.innerHTML =
        '<div class="text-violet-300/90 truncate">' +
        escapeHtml(m.chunk_name || c.chunk_id) +
        '</div>' +
        '<div class="text-slate-500 truncate">' +
        escapeHtml(m.chunk_type || '') +
        ' · ' +
        escapeHtml(c.collection || '') +
        (truncated ? ' <span class="text-amber-400">[truncated 100k]</span>' : '') +
        '</div>' +
        '<div class="text-slate-600 truncate">' +
        escapeHtml(preview) +
        '</div>';
      row.addEventListener('click', () => showMetaForChunk(c.chunk_id, true));
      wrap.appendChild(row);
    }
  }

  async function openChunkFile(relPath) {
    const dbEl = $('chunkInspectDbPath');
    const dbParam = dbEl && dbEl.value.trim() ? dbEl.value.trim() : '';
    const sb = chunkSourceBaseParam();

    const rawQ = new URLSearchParams({ path: relPath });
    if (sb) rawQ.set('source_base', sb);

    const chunkQ = new URLSearchParams({ path: relPath });
    if (dbParam) chunkQ.set('db_path', dbParam);
    if (sb) chunkQ.set('source_base', sb);

    const totalEl = $('chunkTotalLabel');
    const codeEl = $('chunkVisualizerCode');
    const hintEl = $('chunkInspectorHint');
    if (totalEl) totalEl.textContent = '…';
    if (codeEl) codeEl.innerHTML = '<span class="text-slate-500">Loading…</span>';
    if (hintEl) hintEl.textContent = '';

    try {
      const [rawR, chunkR] = await Promise.all([
        fetch('/api/file/raw?' + rawQ),
        fetch('/api/chunks/file?' + chunkQ),
      ]);
      if (!rawR.ok) {
        const err = await rawR.text();
        if (codeEl) codeEl.textContent = 'Failed to load file: ' + err;
        chunkState = null;
        if (!catalogLocked) {
          renderChunkList([], relPath);
        }
        if (totalEl) totalEl.textContent = '0';
        return;
      }
      const rawText = await rawR.text();
      let chunkJ = { chunks: [], abs_source: '', total_chunks: 0 };
      if (chunkR.ok) {
        try {
          chunkJ = await chunkR.json();
        } catch (parseErr) {
          if (hintEl) hintEl.textContent = 'DB error: invalid JSON from /api/chunks/file — ' + String(parseErr);
        }
      } else {
        const errText = await chunkR.text().catch(() => chunkR.statusText);
        let detail = errText.slice(0, 300);
        try {
          const ej = JSON.parse(errText);
          if (ej.detail) detail = String(ej.detail).slice(0, 300);
        } catch (_) {}
        if (hintEl) hintEl.textContent = `DB error (${chunkR.status}): ${detail}`;
      }
      const chunks = chunkJ.chunks || [];
      const displayNorm = normalizeNewlines(rawText);
      chunkState = {
        chunks,
        path: relPath,
        absSource: chunkJ.abs_source || '',
        rawNorm: displayNorm,
      };

      if (hintEl && chunkR.ok) {
        hintEl.textContent =
          'abs_source: ' + (chunkJ.abs_source || '—') + ' · matches require ingest from this path.';
      }
      if (totalEl) totalEl.textContent = String(chunkJ.total_chunks != null ? chunkJ.total_chunks : chunks.length);

      const intervals = buildIntervals(displayNorm, chunks);
      if (codeEl) codeEl.innerHTML = buildHighlightedHtml(displayNorm, intervals);

      if (!catalogLocked) {
        renderChunkList(chunks, relPath);
      } else if (totalEl) {
        totalEl.textContent = String(chunks.length) + ' in file (catalog below)';
      }

      await syncExplorerToOpenedFile(relPath);

      $('chunkMetaFloat')?.classList.add('hidden');
      selectedChunkId = null;
    } catch (e) {
      console.error(e);
      if (codeEl) codeEl.textContent = String(e);
      chunkState = null;
      if (!catalogLocked) {
        renderChunkList([], relPath);
      }
      if (totalEl) totalEl.textContent = '0';
    }
  }

  function destroyChunkSplits() {
    try {
      if (chunkSplitH && typeof chunkSplitH.destroy === 'function') {
        chunkSplitH.destroy(false, false);
      }
    } catch (_) {}
    try {
      if (chunkSplitV && typeof chunkSplitV.destroy === 'function') {
        chunkSplitV.destroy(false, false);
      }
    } catch (_) {}
    chunkSplitH = null;
    chunkSplitV = null;
  }

  /** Re-apply saved percentages after the tab is visible (fixes 0-width first init). */
  function reflowChunkSplits() {
    try {
      if (chunkSplitH && typeof chunkSplitH.getSizes === 'function' && typeof chunkSplitH.setSizes === 'function') {
        chunkSplitH.setSizes(chunkSplitH.getSizes());
      }
    } catch (_) {}
    try {
      if (chunkSplitV && typeof chunkSplitV.getSizes === 'function' && typeof chunkSplitV.setSizes === 'function') {
        chunkSplitV.setSizes(chunkSplitV.getSizes());
      }
    } catch (_) {}
  }

  function ensureChunkSplits() {
    if (typeof Split === 'undefined') return;
    if (chunkSplitH) return;
    const left = $('ci-left-col');
    const right = $('ci-right-viz');
    const top = $('ci-top-explorer');
    const bot = $('ci-bottom-chunks');
    if (!left || !right || !top || !bot) return;
    try {
      chunkSplitH = Split([left, right], {
        sizes: JSON.parse(sessionStorage.getItem('ci_split_h') || '[38, 62]'),
        minSize: [220, 260],
        gutterSize: 8,
        snapOffset: 0,
        onDragEnd: () => {
          if (chunkSplitH) sessionStorage.setItem('ci_split_h', JSON.stringify(chunkSplitH.getSizes()));
        },
      });
      chunkSplitV = Split([top, bot], {
        direction: 'vertical',
        sizes: JSON.parse(sessionStorage.getItem('ci_split_v') || '[52, 48]'),
        minSize: [200, 140],
        gutterSize: 6,
        snapOffset: 0,
        onDragEnd: () => {
          if (chunkSplitV) sessionStorage.setItem('ci_split_v', JSON.stringify(chunkSplitV.getSizes()));
        },
      });
    } catch (e) {
      console.warn('Split.js init', e);
    }
  }

  function wireMetaDrag() {
    const panel = $('chunkMetaFloat');
    const head = $('chunkMetaDragHeader');
    if (!panel || !head) return;
    head.addEventListener('mousedown', (ev) => {
      metaDrag.on = true;
      metaDrag.sx = ev.clientX;
      metaDrag.sy = ev.clientY;
      const r = panel.getBoundingClientRect();
      metaDrag.elx = r.left;
      metaDrag.ely = r.top;
      panel.style.right = 'auto';
      panel.style.bottom = 'auto';
      panel.style.left = metaDrag.elx + 'px';
      panel.style.top = metaDrag.ely + 'px';
      ev.preventDefault();
    });
    window.addEventListener('mousemove', (ev) => {
      if (!metaDrag.on) return;
      const dx = ev.clientX - metaDrag.sx;
      const dy = ev.clientY - metaDrag.sy;
      panel.style.left = metaDrag.elx + dx + 'px';
      panel.style.top = metaDrag.ely + dy + 'px';
    });
    window.addEventListener('mouseup', () => {
      metaDrag.on = false;
    });
  }

  function initChunkInspector() {
    $('chunkBrowseUp')?.addEventListener('click', () => {
      const parts = chunkBrowseRel.split('/').filter(Boolean);
      parts.pop();
      chunkBrowseRel = parts.join('/');
      loadChunkBrowse();
    });
    $('chunkBrowseList')?.addEventListener('dblclick', () => {
      const sel = $('chunkBrowseList');
      const opt = sel?.options[sel.selectedIndex];
      if (!opt || opt.disabled) return;
      if (opt.dataset.type === 'directory') {
        chunkBrowseRel = opt.value;
        loadChunkBrowse();
      } else if (opt.dataset.type === 'file') {
        catalogLocked = false;
        openChunkFile(opt.value);
      }
    });
    $('chunkBtnOpenFile')?.addEventListener('click', () => {
      const sel = $('chunkBrowseList');
      const opt = sel?.options[sel.selectedIndex];
      if (!opt || opt.disabled || opt.dataset.type !== 'file') return;
      catalogLocked = false;
      openChunkFile(opt.value);
    });
    $('chunkBtnRefresh')?.addEventListener('click', () => {
      if (catalogLocked && dbCatalogChunks) {
        void connectChunkDatabase();
        return;
      }
      const sel = $('chunkBrowseList');
      const opt = sel?.options[sel.selectedIndex];
      if (opt && opt.dataset.type === 'file') openChunkFile(opt.value);
      else loadChunkBrowse();
    });
    $('chunkBtnConnectDb')?.addEventListener('click', () => {
      void connectChunkDatabase();
    });
    $('chunkBtnToggleLeft')?.addEventListener('click', () => {
      $('ci-left-col')?.classList.toggle('hidden');
    });
    $('chunkBtnToggleRight')?.addEventListener('click', () => {
      $('ci-right-viz')?.classList.toggle('hidden');
    });
    $('chunkBtnCloseMeta')?.addEventListener('click', () => {
      $('chunkMetaFloat')?.classList.add('hidden');
    });

    const vizScroll = $('chunkVizScroll');
    if (vizScroll) {
      vizScroll.addEventListener(
        'pointerdown',
        () => {
          try {
            vizScroll.focus({ preventScroll: true });
          } catch (_) {
            vizScroll.focus();
          }
        },
        true
      );
    }

    $('chunkVisualizerCode')?.addEventListener('click', (ev) => {
      const t = ev.target;
      if (t && t.closest && t.closest('mark.chunk-mark')) {
        const m = t.closest('mark.chunk-mark');
        const id = m.getAttribute('data-chunk-id');
        if (id) showMetaForChunk(id, true);
      }
    });

    wireMetaDrag();

  }

  window.initChunkInspector = initChunkInspector;
  window.ensureChunkSplits = ensureChunkSplits;
  window.destroyChunkSplits = destroyChunkSplits;
  window.reflowChunkSplits = reflowChunkSplits;
  window.loadChunkBrowseForInspector = loadChunkBrowse;
})();
