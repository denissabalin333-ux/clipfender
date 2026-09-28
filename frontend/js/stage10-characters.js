(() => {
  'use strict';
  const root = document.querySelector('[data-character-query]');
  if (!root) return;
  const query = root.dataset.characterQuery || '';
  const host = document.getElementById('cf10CharacterResults');
  const status = document.getElementById('cf10MaterialsStatus');
  const empty = document.getElementById('cf10CharacterEmpty');
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));

  const formatScore = (video) => {
    if (video.score_estimated) return '<span class="cf10-score-estimated">ОЦЕНКА НЕПОЛНАЯ</span>';
    return `<span>Edit Suitability ${Math.round(Number(video.edit_suitability_score || 0))}/100</span>`;
  };

  async function load() {
    try {
      const response = await fetch(`/api/search?query=${encodeURIComponent(query)}&limit=6&sort=score`, {headers:{Accept:'application/json'}});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const results = Array.isArray(payload.results) ? payload.results : [];
      if (status) status.textContent = results.length ? `Найдено: ${results.length}` : 'Материалов пока нет';
      if (!results.length) { if (empty) empty.hidden = false; return; }
      if (empty) empty.hidden = true;
      if (!host) return;
      host.innerHTML = results.map((video) => `
        <article class="cf10-video-card">
          <img src="${esc(video.thumbnail || '/static/assets/reference/final-real/world-castle-real.webp')}" loading="lazy" alt="">
          <h3>${esc(video.title || 'Без названия')}</h3>
          <div class="cf10-video-meta"><span>${esc(video.channel || 'YouTube')}</span>${formatScore(video)}</div>
          <div class="cf10-video-actions"><a href="/video?id=${encodeURIComponent(video.id)}">ОТКРЫТЬ</a><a href="${esc(video.url || '#')}" target="_blank" rel="noopener noreferrer">YOUTUBE ↗</a></div>
        </article>`).join('');
    } catch (error) {
      if (status) status.textContent = 'Не удалось загрузить материалы';
      if (empty) { empty.hidden = false; empty.querySelector('strong').textContent = 'Архив временно недоступен.'; }
    }
  }

  load();
})();
