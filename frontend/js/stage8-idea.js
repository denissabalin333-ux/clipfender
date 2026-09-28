(() => {
  'use strict';

  const qs = (selector, root = document) => root.querySelector(selector);
  const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));

  function goSearch(query = '', mode = 'search') {
    const params = new URLSearchParams();
    if (String(query).trim()) params.set('q', String(query).trim());
    params.set('mode', mode);
    window.location.href = `/search?${params.toString()}`;
  }

  function setupHome() {
    const form = qs('#homeStage3Search');
    const input = qs('#homeStage3Query');
    if (!form || !input || form.dataset.cf8Ready) return;
    form.dataset.cf8Ready = '1';
    qsa('.home-stage3__hint').forEach(hint => {
      hint.setAttribute('role', 'button');
      hint.setAttribute('tabindex', '0');
      const activate = () => goSearch(hint.textContent.trim(), 'search');
      hint.addEventListener('click', activate);
      hint.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); }
      });
    });
  }

  function setupSearchPage() {
    const root = qs('.cf8-page');
    const form = qs('#cf8SearchForm');
    if (!root || !form) return;

    const params = new URLSearchParams(window.location.search);
    let mode = params.get('mode') === 'idea' ? 'idea' : 'search';
    const query = qs('#cf8Query');
    const film = qs('#cf8Film');
    const mood = qs('#cf8Mood');
    const tempo = qs('#cf8Tempo');
    const genre = qs('#cf8Genre');
    const character = qs('#cf8Character');
    const limit = qs('#cf8Limit');
    const randomIdea = qs('#cf8RandomIdea');
    const status = qs('#cf8Status');
    const results = qs('#cf8Results');
    const title = qs('#cf8Title');
    const lead = qs('#cf8Lead');

    const setMode = nextMode => {
      mode = nextMode === 'idea' ? 'idea' : 'search';
      qsa('[data-cf-mode]').forEach(link => link.classList.toggle('is-active', link.dataset.cfMode === mode));
      qsa('.cf8-idea-only').forEach(node => { node.hidden = mode !== 'idea'; });
      if (mode === 'idea') {
        title.textContent = 'Собери сценарий эдита';
        lead.textContent = 'Задай фильм или сериал, персонажа, жанр, настроение и темп. ClipFender соберёт сценарий и автоматически найдёт реальные материалы под него.';
      } else {
        title.textContent = 'Полноэкранный поиск материалов';
        lead.textContent = 'Обычный режим использует тот же backend-поиск, что и архив, но не заставляет тебя уходить в старую страницу.';
      }
    };

    qsa('[data-cf-mode]').forEach(link => {
      link.addEventListener('click', event => {
        const targetMode = link.dataset.cfMode;
        if (!targetMode) return;
        event.preventDefault();
        const next = new URL('/search', window.location.origin);
        next.searchParams.set('mode', targetMode);
        if (query.value.trim()) next.searchParams.set('q', query.value.trim());
        if (film.value.trim()) next.searchParams.set('film', film.value.trim());
        if (mood.value && targetMode === 'idea') next.searchParams.set('mood', mood.value);
        if (tempo.value && targetMode === 'idea') next.searchParams.set('tempo', tempo.value);
        if (genre.value && targetMode === 'idea') next.searchParams.set('genre', genre.value);
        if (character.value.trim() && targetMode === 'idea') next.searchParams.set('character', character.value.trim());
        window.history.pushState({}, '', next);
        setMode(targetMode);
        run();
      });
    });

    qsa('[data-query]').forEach(button => button.addEventListener('click', () => {
      query.value = button.dataset.query || '';
      run();
    }));

    function updateIdeaUrl() {
      const next = new URL('/search', window.location.origin);
      next.searchParams.set('mode', mode);
      if (query.value.trim()) next.searchParams.set('q', query.value.trim());
      if (film.value.trim()) next.searchParams.set('film', film.value.trim());
      if (mode === 'idea') {
        if (mood.value) next.searchParams.set('mood', mood.value);
        if (tempo.value) next.searchParams.set('tempo', tempo.value);
        if (genre.value) next.searchParams.set('genre', genre.value);
        if (character.value.trim()) next.searchParams.set('character', character.value.trim());
      }
      window.history.replaceState({}, '', next);
    }

    function setupRandomIdea() {
      if (!randomIdea || randomIdea.dataset.cf10Ready) return;
      randomIdea.dataset.cf10Ready = '1';
      const characters = ['Джон Сноу', 'Джейми Ланнистер', 'Дейенерис Таргариен', 'Тирион Ланнистер', 'Арья Старк', 'Серсея Ланнистер'];
      const genres = ['action', 'drama', 'romance', 'horror_tragedy', 'comedy', 'adventure'];
      const moods = ['action', 'dark', 'drama', 'romance', 'emotional', 'epic', 'tension', 'melancholy'];
      const tempos = ['fast', 'medium', 'slow'];
      const pick = list => list[Math.floor(Math.random() * list.length)];
      randomIdea.addEventListener('click', () => {
        mode = 'idea';
        query.value = '';
        film.value = 'Game of Thrones';
        character.value = pick(characters);
        genre.value = pick(genres);
        mood.value = pick(moods);
        tempo.value = pick(tempos);
        setMode('idea');
        updateIdeaUrl();
        run();
      });
    }

    function enableStoryboardPrint() {
      window.print();
    }

    async function run() {
      const q = query.value.trim();
      const f = film.value.trim();
      results.innerHTML = '<div class="cf8-empty">Загружаю материалы…</div>';
      status.textContent = 'Поиск…';
      try {
        let url;
        if (mode === 'idea') {
          const api = new URL('/api/edit-idea', window.location.origin);
          if (q) api.searchParams.set('query', q);
          if (f) api.searchParams.set('film', f);
          if (mood.value) api.searchParams.set('mood', mood.value);
          if (tempo.value) api.searchParams.set('tempo', tempo.value);
          if (genre.value) api.searchParams.set('genre', genre.value);
          if (character.value.trim()) api.searchParams.set('character', character.value.trim());
          api.searchParams.set('limit_per_stage', limit.value);
          url = api;
        } else {
          const api = new URL('/api/search', window.location.origin);
          api.searchParams.set('query', q || 'cinematic');
          if (f) api.searchParams.set('film', f);
          api.searchParams.set('sort', 'score');
          api.searchParams.set('limit', '20');
          api.searchParams.set('page', '1');
          url = api;
        }
        const response = await fetch(url);
        const data = await response.json();
        if (!response.ok) throw new Error(data?.detail || data?.error || 'Не удалось загрузить результаты.');
        if (mode === 'idea') renderIdea(data);
        else renderSearch(data);
      } catch (error) {
        results.innerHTML = `<div class="cf8-empty">${esc(error.message)}</div>`;
        status.textContent = 'Ошибка';
      }
    }

    function renderSearch(data) {
      const list = Array.isArray(data.results) ? data.results : [];
      status.textContent = `Найдено: ${data.filtered_total ?? list.length}. Backend уже отсортировал материалы по Edit Suitability.`;
      if (!list.length) {
        results.innerHTML = '<div class="cf8-empty">Материалов нет. Сначала выполни поиск в архиве или измени запрос.</div>';
        return;
      }
      results.innerHTML = list.map(video => `
        <article class="cf8-result-card">
          <div class="cf8-thumb"><img src="${esc(video.thumbnail || '')}" alt="" loading="lazy"></div>
          <div>
            <h2 class="cf8-result-title">${esc(video.title || 'Без названия')}</h2>
            <div class="cf8-meta">${esc(video.channel || 'Источник YouTube')} · ${esc(video.duration || '')} · ${video.score_estimated ? 'оценка по доступным сигналам' : 'расчётный score'}</div>
            <div class="cf8-card-actions"><a href="${esc(video.url || '#')}" target="_blank" rel="noopener noreferrer">ОТКРЫТЬ YOUTUBE</a><a href="/archive?q=${encodeURIComponent(data.query || '')}&film=${encodeURIComponent(data.film || '')}" data-cf-hard-nav>ОТКРЫТЬ В АРХИВЕ</a></div>
          </div>
          <div class="cf8-score"><b>${Number(video.edit_suitability_score ?? 0)}/100</b><span>Edit Suitability</span>${video.score_estimated ? '<i class="cf8-estimated">estimated</i>' : ''}</div>
        </article>
      `).join('');
    }

    function renderIdea(data) {
      const searchState = data.material_search?.performed
        ? `Материалы автоматически найдены: ${data.material_search.loaded || 0} · живой поиск YouTube`
        : 'Материалы взяты из локального кэша';
      status.textContent = data.status === 'no_material'
        ? 'Подходящих реальных материалов пока недостаточно.'
        : `Сценарий собран из ${data.candidate_total || 0} реальных материалов. ${searchState}.`;
      if (!Array.isArray(data.stages) || !data.stages.length) {
        results.innerHTML = `<div class="cf8-empty">${esc(data.message || 'Нет подходящих материалов.')}</div>`;
        return;
      }
      results.innerHTML = `
        <section class="cf8-scenario-head">
          <div class="cf8-scenario-head__topline">
            <span class="cf8-kicker">СЦЕНАРИЙ ЭДИТА · STAGE 10</span>
            <button type="button" class="cf8-print-button" id="cf8PrintStoryboard">↓ СКАЧАТЬ РАСКАДРОВКУ</button>
          </div>
          <h2>${esc(data.character || data.query || data.film || 'Без имени')}</h2>
          <p class="cf8-scenario-head__summary">${esc(data.film || 'Фильм / сериал не указан')} · ${esc(data.genre ? data.genre.replace('_', ' / ') : 'жанр не указан')} · ${esc(data.mood || 'любое настроение')} · ${esc(data.tempo || 'любой темп')}</p>
          <p>${esc(data.note || '')}</p>
          <div class="cf8-scenario-searchline"><span>АВТОПОИСК</span><b>${esc(data.scenario_query || '')}</b><em>${esc(searchState)}</em></div>
        </section>
        <div class="cf8-scenario">
          ${data.stages.map(stage => `
            <section class="cf8-stage" data-stage-key="${esc(stage.key || '')}">
              <div class="cf8-stage__head">
                <div><span class="cf8-kicker">${esc(stage.number)}</span><h3>${esc(stage.label || stage.title || '')}</h3><b>${esc(stage.title || '')}</b></div>
                <div class="cf8-stage__description"><p>${esc(stage.description || '')}</p><span>${esc(stage.search_focus || '')}</span></div>
              </div>
              <div class="cf8-stage__grid">
                ${stage.items.map((item, index) => `
                  <article class="cf8-stage-card">
                    <div class="cf8-stage-card__number">${String(index + 1).padStart(2, '0')}</div>
                    <div class="cf8-stage-card__img"><img src="${esc(item.thumbnail || '')}" alt="" loading="lazy"></div>
                    <div class="cf8-stage-card__body">
                      <div class="cf8-stage-card__eyebrow">${esc(stage.label || '')} · SHOT ${String(index + 1).padStart(2, '0')}</div>
                      <h4>${esc(item.title || 'Без названия')}</h4>
                      <p>${esc(item.source || 'Источник YouTube')} · ${esc(item.duration || '')} · ${esc(item.timecode || '')}</p>
                      <div class="cf8-stage-card__score">${Number(item.edit_suitability_score || 0)}/100 · Edit Suitability${item.score_estimated ? ' · estimated' : ''}</div>
                      <div class="cf8-stage-card__why">${esc(item.why || '')}</div>
                      <a href="${esc(item.url || '#')}" target="_blank" rel="noopener noreferrer">ОТКРЫТЬ ИСТОЧНИК →</a>
                    </div>
                  </article>
                `).join('')}
              </div>
              <div class="cf8-stage__connector" aria-hidden="true"><span>↓</span></div>
            </section>
          `).join('')}
        </div>
      `;
      const printButton = qs('#cf8PrintStoryboard', results);
      if (printButton) printButton.addEventListener('click', enableStoryboardPrint);
    }


    form.addEventListener('submit', event => { event.preventDefault(); updateIdeaUrl(); run(); });
    setupRandomIdea();
    history.replaceState({}, '', window.location.href);
    setMode(mode);
    if (params.get('q')) query.value = params.get('q');
    if (params.get('film')) film.value = params.get('film');
    if (params.get('mood')) mood.value = params.get('mood');
    if (params.get('tempo')) tempo.value = params.get('tempo');
    if (params.get('genre')) genre.value = params.get('genre');
    if (params.get('character')) character.value = params.get('character');
    if (query.value || params.get('mode') === 'idea' || film.value || character.value) run();
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupHome();
    setupSearchPage();
  });
})();
