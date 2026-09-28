(() => {
  'use strict';

  // One final visual/interaction layer. It never removes application handlers.
  const qs = (s, r = document) => r.querySelector(s);
  const qsa = (s, r = document) => [...r.querySelectorAll(s)];

  // Remove obsolete decorative elements only when they are purely visual arrows/shapes.
  qsa('.hero-arrow,.decor-arrow,[data-decor-arrow]').forEach(el => el.remove());

  // Idea finder: search, categories, popular queries, details, favorites.
  const ideaInput = qs('#cfIdeaSearchV7');
  const ideaSearchButton = qs('#cfIdeaSearchButtonV7');
  const ideaCards = qsa('[data-v7-idea]');
  const ideaMeta = qs('#cfIdeaMetaV7');
  const empty = qs('#cfIdeaEmptyV7');
  const modalHost = qs('#cfIdeaModalV7');
  let favorites = [];
  try { favorites = JSON.parse(localStorage.getItem('clipfender_idea_favorites_v7') || '[]'); } catch {}

  const normalize = (v) => String(v || '').toLowerCase().replace(/ё/g,'е').trim();
  function applyIdeas() {
    const query = normalize(ideaInput?.value);
    const active = qs('[data-v7-idea-cat].active')?.dataset.v7IdeaCat || 'all';
    let visible = 0;
    ideaCards.forEach(card => {
      const hay = normalize(`${card.dataset.source||''} ${card.dataset.title||''} ${card.dataset.tags||''} ${card.textContent||''}`);
      const cats = (card.dataset.category || '').split(/\s+/);
      const show = (active === 'all' || cats.includes(active)) && (!query || hay.includes(query));
      card.hidden = !show;
      if (show) visible++;
      const fav = favorites.includes(card.dataset.key);
      const btn = qs('[data-v7-favorite]', card);
      if (btn) btn.textContent = fav ? '★ СОХРАНЕНО' : '☆ СОХРАНИТЬ';
      if (btn) btn.classList.toggle('is-active', fav);
    });
    if (ideaMeta) ideaMeta.textContent = `ПОКАЗАНО ИДЕЙ: ${visible}`;
    if (empty) empty.hidden = visible !== 0;
  }
  function openIdea(card) {
    if (!modalHost) return;
    const title = card.dataset.title || 'Идея для эдита';
    const source = card.dataset.source || '';
    const description = card.dataset.description || card.querySelector('p')?.textContent || '';
    const formula = card.dataset.formula || 'вступление → развитие → кульминация → финал';
    const q = card.dataset.query || source;
    modalHost.innerHTML = `<div class="cf-v7-modal-backdrop" data-v7-close></div><div class="cf-v7-modal"><button type="button" class="cf-v7-modal__close" data-v7-close aria-label="Закрыть">×</button><span>ИЗ МОНТАЖНОЙ МАСТЕРСКОЙ</span><h2>${title}</h2><p>${description}</p><div class="cf-v7-modal__grid"><div><b>МОНТАЖНАЯ ФОРМУЛА</b><p>${formula}</p></div><div><b>ИСТОЧНИК</b><p>${source}</p></div></div><div class="cf-v7-modal__actions"><a class="cf-v7-btn" href="/archive?q=${encodeURIComponent(q)}">НАЙТИ СЦЕНЫ</a><button class="cf-v7-btn cf-v7-btn--gold" type="button" data-v7-modal-fav data-key="${card.dataset.key}">СОХРАНИТЬ ИДЕЮ</button></div></div>`;
    modalHost.hidden = false;
    const favBtn = qs('[data-v7-modal-fav]', modalHost);
    if (favorites.includes(card.dataset.key)) favBtn.textContent = 'СОХРАНЕНО';
    favBtn?.addEventListener('click', () => {
      const key = card.dataset.key;
      const idx = favorites.indexOf(key);
      if (idx >= 0) { favorites.splice(idx,1); favBtn.textContent = 'СОХРАНИТЬ ИДЕЮ'; }
      else { favorites.push(key); favBtn.textContent = 'СОХРАНЕНО'; }
      localStorage.setItem('clipfender_idea_favorites_v7', JSON.stringify(favorites));
      applyIdeas();
      window.showToast?.(idx >= 0 ? 'Идея удалена из сохранённых.' : 'Идея сохранена.', 'success');
    });
    qsa('[data-v7-close]', modalHost).forEach(el => el.addEventListener('click', () => { modalHost.hidden = true; modalHost.innerHTML=''; }));
    qs('.cf-v7-modal__close', modalHost)?.focus();
  }
  qsa('[data-v7-idea-cat]').forEach(btn => btn.addEventListener('click', () => {
    qsa('[data-v7-idea-cat]').forEach(x => x.classList.remove('active'));
    btn.classList.add('active'); applyIdeas();
  }));
  qsa('[data-v7-idea-popular]').forEach(btn => btn.addEventListener('click', () => {
    if (ideaInput) { ideaInput.value = btn.dataset.v7IdeaPopular || ''; applyIdeas(); ideaInput.focus(); }
  }));
  ideaInput?.addEventListener('input', applyIdeas);
  ideaInput?.addEventListener('keydown', e => { if (e.key==='Enter') { e.preventDefault(); applyIdeas(); } });
  ideaSearchButton?.addEventListener('click', () => {
    applyIdeas();
    const query = String(ideaInput?.value || '').trim();
    if (query && !ideaCards.some(card => !card.hidden)) {
      location.href = `/archive?q=${encodeURIComponent(query + ' cinematic edit')}`;
    }
  });
  qsa('[data-v7-idea-open]').forEach(btn => btn.addEventListener('click', () => openIdea(btn.closest('[data-v7-idea]'))));
  qsa('[data-v7-favorite]').forEach(btn => btn.addEventListener('click', () => {
    const card = btn.closest('[data-v7-idea]'); if (!card) return;
    const key = card.dataset.key; const idx = favorites.indexOf(key);
    if (idx >= 0) favorites.splice(idx,1); else favorites.push(key);
    localStorage.setItem('clipfender_idea_favorites_v7', JSON.stringify(favorites));
    applyIdeas(); window.showToast?.(idx >= 0 ? 'Идея удалена.' : 'Идея сохранена.', 'success');
  }));
  applyIdeas();

  // Guides mini-search hands off to the existing archive/search flow.
  const guideForm = qs('#cfGuideSearchV7');
  guideForm?.addEventListener('submit', e => {
    e.preventDefault();
    const q = String(qs('input', guideForm)?.value || '').trim();
    if (!q) return qs('input', guideForm)?.focus();
    location.href = `/archive?q=${encodeURIComponent(q)}`;
  });

  // Prevent stale visual layers from taking over after a route change.
  document.documentElement.classList.add('cf-v7-ready');
})();
