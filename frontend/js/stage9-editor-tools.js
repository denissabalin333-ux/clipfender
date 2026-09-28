(() => {
  'use strict';
  const api = async (path, options = {}) => {
    const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { Accept: 'application/json', ...(options.headers || {}) } });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try { const data = await response.json(); if (data?.detail) message = Array.isArray(data.detail) ? data.detail.map(x => x.msg || '').join('; ') : String(data.detail); } catch (_) {}
      const error = new Error(message); error.status = response.status; throw error;
    }
    return response.json();
  };
  const csrf = async () => {
    if (window.ensureCsrfToken) return window.ensureCsrfToken();
    await fetch('/api/auth/csrf', { credentials: 'same-origin' });
    return document.cookie.split('; ').find(x => x.startsWith('cf_csrf='))?.split('=')[1] || '';
  };
  const post = async (path, payload) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': await csrf() }, body: JSON.stringify(payload) });
  const del = async (path) => api(path, { method: 'DELETE', headers: { 'X-CSRF-Token': await csrf() } });
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
  const seconds = value => Math.max(0, Number(value) || 0);
  const fmt = value => { const s = Math.floor(seconds(value)); const m = Math.floor(s / 60); const r = s % 60; return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`; };

  function panelMarkup(title, body) { return `<section class="cf-stage9-panel"><h4>${esc(title)}</h4>${body}</section>`; }

  function explanationMarkup(data) {
    const c = data.components || {};
    const rows = [
      ['Edit Score', c.edit_score?.value ?? 0, c.edit_score?.max ?? 45, `исходный ${c.edit_score?.source ?? 0}/100`],
      ['Материал', c.material?.value ?? 0, c.material?.max ?? 20, (c.material?.signals || []).join(', ') || 'сигналов нет'],
      ['Качество', c.quality?.value ?? 0, c.quality?.max ?? 15, (c.quality?.signals || []).join(', ') || 'сигналов нет'],
      ['Длительность', c.duration?.value ?? 0, c.duration?.max ?? 10, c.duration?.label || ''],
      ['Релевантность', c.relevance?.value ?? 0, c.relevance?.max ?? 10, [c.relevance?.query, c.relevance?.film].filter(Boolean).join(' · ') || 'нет уточнения'],
      ['Аудио / сцена', c.audio_scene?.value ?? 0, c.audio_scene?.max ?? 5, (c.audio_scene?.signals || []).join(', ') || 'сигналов нет'],
      ['Штрафы', c.penalties?.value ?? 0, '', (c.penalties?.signals || []).join(', ') || 'нет'],
    ];
    const grid = rows.map(row => `<div class="cf-stage9-component"><strong>${esc(row[0])}: ${esc(row[1])}${row[2] ? ` / ${esc(row[2])}` : ''}</strong><small>${esc(row[3])}</small></div>`).join('');
    return panelMarkup('ПОЧЕМУ ЭТОТ МАТЕРИАЛ ПОДХОДИТ', `<span class="cf-stage9-score-badge">Edit Suitability ${esc(data.score)}/100</span>${data.estimated ? '<span class="cf-stage9-score-badge cf-stage9-estimated">Оценка рассчитана по неполному набору данных</span>' : ''}<div class="cf-stage9-grid" style="margin-top:10px">${grid}</div><p class="cf-stage9-muted cf-stage9-inline">${esc(data.note || '')}</p>`);
  }

  function similarMarkup(data) {
    if (!data.items?.length) return panelMarkup('ПОХОЖИЕ МАТЕРИАЛЫ', '<p class="cf-stage9-muted">Похожих реальных записей в локальной базе пока нет.</p>');
    const items = data.items.map(item => `<a href="/video?id=${encodeURIComponent(item.video_id)}"><img src="${esc(item.thumbnail || `https://i.ytimg.com/vi/${encodeURIComponent(item.video_id)}/hqdefault.jpg`)}" alt="${esc(item.title)}" loading="lazy"><span><strong>${esc(item.title || 'Без названия')}</strong><br><small>${esc(item.source || '')} · Suitability ${esc(item.edit_suitability_score)}/100${item.score_estimated ? ' · estimated' : ''}</small></span></a>`).join('');
    return panelMarkup('ПОХОЖИЕ МАТЕРИАЛЫ', `<div class="cf-stage9-similar">${items}</div>`);
  }

  function bookmarkForm(videoId, existing) {
    const list = existing?.length ? existing.map(item => `<div class="cf-stage9-bookmark"><div><div class="cf-stage9-bookmark__time">${fmt(item.start_seconds)} → ${fmt(item.end_seconds)}</div><div>${esc(item.note || 'Без заметки')}</div></div><button type="button" data-delete-bookmark="${item.id}">×</button></div>`).join('') : '<div class="cf-stage9-muted">Пока нет закладок для этого материала.</div>';
    return panelMarkup('ТАЙМКОДЫ-ЗАКЛАДКИ', `<form class="cf-stage9-form" data-bookmark-form="${esc(videoId)}"><label>Начало, сек.<input name="start_seconds" type="number" min="0" step="0.1" value="0" required></label><label>Конец, сек.<input name="end_seconds" type="number" min="0.1" step="0.1" value="5" required></label><textarea name="note" maxlength="500" placeholder="Что нужно сохранить из этого момента?"></textarea><button type="submit">СОХРАНИТЬ ЗАКЛАДКУ</button></form><div class="cf-stage9-bookmarks">${list}</div>`);
  }

  async function loadBookmarkPanel(videoId, video) {
    const host = document.querySelector('[data-stage9-bookmarks-host]');
    if (!host) return;
    try {
      const data = await api('/api/library/bookmarks?video_id=' + encodeURIComponent(videoId));
      host.innerHTML = bookmarkForm(videoId, data.items || []);
      host.querySelector('[data-bookmark-form]')?.addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const start = seconds(form.start_seconds.value), end = seconds(form.end_seconds.value);
        if (end <= start) { window.showToast?.('Конец таймкода должен быть позже начала.', 'error'); return; }
        try { await post('/api/library/bookmarks', { video_id: videoId, start_seconds: start, end_seconds: end, note: form.note.value, video }); await loadBookmarkPanel(videoId, video); window.showToast?.('Закладка сохранена.', 'success'); }
        catch (error) { window.showToast?.(error.message || 'Не удалось сохранить закладку.', 'error'); }
      });
      host.querySelectorAll('[data-delete-bookmark]').forEach(button => button.addEventListener('click', async () => {
        try { await del('/api/library/bookmarks/' + button.dataset.deleteBookmark); await loadBookmarkPanel(videoId, video); } catch (error) { window.showToast?.(error.message || 'Не удалось удалить закладку.', 'error'); }
      }));
    } catch (error) {
      host.innerHTML = panelMarkup('ТАЙМКОДЫ-ЗАКЛАДКИ', `<p class="cf-stage9-muted">${error.status === 401 ? 'Войди в ClipFender, чтобы сохранять таймкоды.' : 'Закладки временно недоступны.'}</p>`);
    }
  }

  async function enhanceArchiveDetails(button) {
    const card = button.closest('.video-card');
    const videoId = card?.dataset.videoId;
    if (!videoId) return;
    setTimeout(async () => {
      const body = document.getElementById('modalBody');
      if (!body) return;
      const video = typeof window.videoStore !== 'undefined' && window.videoStore?.get ? window.videoStore.get(String(videoId)) : { id: videoId };
      body.querySelectorAll('[data-stage9-panel]').forEach(node => node.remove());
      try {
        const [explanation, similar] = await Promise.all([
          api('/api/video/' + encodeURIComponent(videoId) + '/score-explanation'),
          api('/api/video/' + encodeURIComponent(videoId) + '/similar?limit=5'),
        ]);
        body.insertAdjacentHTML('beforeend', explanationMarkup(explanation).replace('<section ', '<section data-stage9-panel '));
        body.insertAdjacentHTML('beforeend', similarMarkup(similar).replace('<section ', '<section data-stage9-panel '));
        body.insertAdjacentHTML('beforeend', '<div data-stage9-bookmarks-host></div>');
        await loadBookmarkPanel(videoId, video || {id: videoId});
      } catch (error) {
        body.insertAdjacentHTML('beforeend', panelMarkup('ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ', `<p class="cf-stage9-muted">${esc(error.message || 'Дополнительные данные недоступны.')}</p>`).replace('<section ', '<section data-stage9-panel '));
      }
    }, 30);
  }

  document.addEventListener('click', event => {
    const details = event.target.closest('.details-button');
    if (details) enhanceArchiveDetails(details);
  }, true);

  function initVideoPage() {
    const id = new URLSearchParams(location.search).get('id');
    const host = document.querySelector('.cf-video-meta');
    if (!id || !host) return;
    const enhance = async () => {
      if (host.querySelector('[data-stage9-panel]')) return;
      try {
        const [explanation, similar] = await Promise.all([
          api('/api/video/' + encodeURIComponent(id) + '/score-explanation'),
          api('/api/video/' + encodeURIComponent(id) + '/similar?limit=6'),
        ]);
        host.insertAdjacentHTML('beforeend', explanationMarkup(explanation).replace('<section ', '<section data-stage9-panel '));
        host.insertAdjacentHTML('beforeend', similarMarkup(similar).replace('<section ', '<section data-stage9-panel '));
        host.insertAdjacentHTML('beforeend', '<div data-stage9-bookmarks-host></div>');
        const video = { id, title: document.getElementById('videoMetaTitle')?.textContent || id, url: document.getElementById('youtubeLink')?.href || '' };
        await loadBookmarkPanel(id, video);
      } catch (error) {
        if (error.status !== 404) host.insertAdjacentHTML('beforeend', panelMarkup('ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ', `<p class="cf-stage9-muted">${esc(error.message || 'Дополнительные данные недоступны.')}</p>`).replace('<section ', '<section data-stage9-panel '));
      }
    };
    setTimeout(enhance, 160);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initVideoPage, {once:true}); else initVideoPage();
})();
