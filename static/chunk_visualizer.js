/**
 * Chunk Inspector: browse files, load Chroma chunks, highlight by exact match (normalized newlines).
 */
(function () {
  const CHUNK_TYPE_COLORS = {
    device_load_function: 'rgba(255, 100, 0, 0.35)',
    matrix_solver_function: 'rgba(0, 200, 50, 0.35)',
    device_setup_function: 'rgba(168, 85, 247, 0.3)',
    core_constant: 'rgba(234, 179, 8, 0.28)',
    file_preamble: 'rgba(148, 163, 184, 0.25)',
    preproc_def: 'rgba(56, 189, 248, 0.22)',
    preproc_function_def: 'rgba(14, 165, 233, 0.22)',
    default: 'rgba(0, 150, 255, 0.22)',
  };

  const $ = (id) => document.getElementById(id);

  let chunkBrowseRel = '';
  let chunkSplitH = null;
  let chunkSplitV = null;
  /** @type {{ chunks: any[], path: string, absSource: string, rawNorm: string } | null} */
  let chunkState = null;
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
    if (!chunkState) return;
    const c = chunkState.chunks.find((x) => x.chunk_id === chunkId);
    if (!c) return;

    selectedChunkId = chunkId;
    document.querySelectorAll('#chunkVisualizerCode mark.chunk-mark').forEach((el) => {
      el.classList.toggle('chunk-mark-selected', el.getAttribute('data-chunk-id') === chunkId);
    });
    document.querySelectorAll('.chunk-list-row').forEach((row) => {
      row.classList.toggle('chunk-list-selected', row.getAttribute('data-chunk-id') === chunkId);
    });

    const m = c.metadata || {};
    const lines = [
      ['chunk_name', m.chunk_name || '—'],
      ['chunk_type', m.chunk_type || '—'],
      ['device_family', m.device_family || '—'],
      ['concepts', m.concepts || '—'],
      ['source_type', m.source_type || '—'],
      ['chunk_index', m.chunk_index || '—'],
      ['collection', c.collection || '—'],
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
      if (mark && typeof mark.scrollIntoView === 'function') {
        mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }

  async function loadChunkBrowse() {
    const q = new URLSearchParams({ path: chunkBrowseRel });
    const r = await fetch('/api/browse?' + q);
    const j = await r.json();
    const pathEl = $('chunkBrowsePath');
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

  function renderChunkList(chunks, path) {
    const wrap = $('chunkListInner');
    if (!wrap) return;
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
    const q = new URLSearchParams({ path: relPath });
    if (dbParam) q.set('db_path', dbParam);

    const totalEl = $('chunkTotalLabel');
    const codeEl = $('chunkVisualizerCode');
    const hintEl = $('chunkInspectorHint');
    if (totalEl) totalEl.textContent = '…';
    if (codeEl) codeEl.innerHTML = '<span class="text-slate-500">Loading…</span>';
    if (hintEl) hintEl.textContent = '';

    try {
      const [rawR, chunkR] = await Promise.all([
        fetch('/api/file/raw?' + new URLSearchParams({ path: relPath })),
        fetch('/api/chunks/file?' + q),
      ]);
      if (!rawR.ok) {
        const err = await rawR.text();
        if (codeEl) codeEl.textContent = 'Failed to load file: ' + err;
        chunkState = null;
        renderChunkList([], relPath);
        if (totalEl) totalEl.textContent = '0';
        return;
      }
      const rawText = await rawR.text();
      const chunkJ = chunkR.ok ? await chunkR.json() : { chunks: [], abs_source: '', total_chunks: 0 };
      const chunks = chunkJ.chunks || [];
      const displayNorm = normalizeNewlines(rawText);
      chunkState = {
        chunks,
        path: relPath,
        absSource: chunkJ.abs_source || '',
        rawNorm: displayNorm,
      };

      if (hintEl) {
        hintEl.textContent =
          'abs_source: ' + (chunkJ.abs_source || '—') + ' · matches require ingest from this path.';
      }
      if (totalEl) totalEl.textContent = String(chunkJ.total_chunks != null ? chunkJ.total_chunks : chunks.length);

      const intervals = buildIntervals(displayNorm, chunks);
      if (codeEl) codeEl.innerHTML = buildHighlightedHtml(displayNorm, intervals);

      renderChunkList(chunks, relPath);

      $('chunkMetaFloat')?.classList.add('hidden');
      selectedChunkId = null;
    } catch (e) {
      console.error(e);
      if (codeEl) codeEl.textContent = String(e);
      chunkState = null;
      renderChunkList([], relPath);
      if (totalEl) totalEl.textContent = '0';
    }
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
        minSize: [180, 220],
        gutterSize: 8,
        snapOffset: 0,
        onDragEnd: () => {
          if (chunkSplitH) sessionStorage.setItem('ci_split_h', JSON.stringify(chunkSplitH.getSizes()));
        },
      });
      chunkSplitV = Split([top, bot], {
        direction: 'vertical',
        sizes: JSON.parse(sessionStorage.getItem('ci_split_v') || '[52, 48]'),
        minSize: [100, 100],
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
        openChunkFile(opt.value);
      }
    });
    $('chunkBtnOpenFile')?.addEventListener('click', () => {
      const sel = $('chunkBrowseList');
      const opt = sel?.options[sel.selectedIndex];
      if (!opt || opt.disabled || opt.dataset.type !== 'file') return;
      openChunkFile(opt.value);
    });
    $('chunkBtnRefresh')?.addEventListener('click', () => {
      const sel = $('chunkBrowseList');
      const opt = sel?.options[sel.selectedIndex];
      if (opt && opt.dataset.type === 'file') openChunkFile(opt.value);
      else loadChunkBrowse();
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
  window.loadChunkBrowseForInspector = loadChunkBrowse;
})();
