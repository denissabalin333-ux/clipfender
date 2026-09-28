(() => {
  'use strict';

  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => [...root.querySelectorAll(sel)];
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));

  const IDEA_DATA = {
    moods: {
      action: { label: 'Экшн', intro: 'Открыть коротким напряжённым кадром, затем быстро увеличить плотность движения.', climax: 'Максимум динамики: бой, преследование, оружие, столкновение.' },
      dark: { label: 'Тёмное', intro: 'Начать с тишины, силуэта или взгляда и не раскрывать конфликт сразу.', climax: 'Кульминация строится на резком контрасте света, движения и угрозы.' },
      drama: { label: 'Драма', intro: 'Дать зрителю время считать эмоцию и отношения между персонажами.', climax: 'Реплика, реакция или решение становятся эмоциональным пиком.' },
      romance: { label: 'Романтика', intro: 'Использовать взгляды, дистанцию и мягкие переходы между персонажами.', climax: 'Свести несколько эмоциональных деталей в один запоминающийся момент.' },
      emotional: { label: 'Эмоциональное', intro: 'Начать с крупного плана и паузы, чтобы сразу задать внутреннее состояние.', climax: 'Повысить интенсивность через реакции, слёзы, потерю или встречу.' },
      epic: { label: 'Эпичное', intro: 'Широкий план или силуэт задаёт масштаб мира.', climax: 'Максимально крупное событие, армия, дракон или визуальный контраст.' },
      tension: { label: 'Напряжение', intro: 'Показывать угрозу частично: деталь → взгляд → пространство.', climax: 'Резкое действие или раскрытие опасности.' },
      melancholy: { label: 'Меланхолия', intro: 'Медленный вход, атмосфера и визуальная тишина.', climax: 'Эмоциональный акцент без резкого ускорения, затем мягкий уход.' },
    },
    tempos: {
      fast: { label: 'Быстрые кадры', cut: '2–5 секунд на монтажный фрагмент; чаще меняй крупность и направление движения.' },
      medium: { label: 'Средний темп', cut: '5–10 секунд; сохраняй читаемость сцены и чередуй действие с реакцией.' },
      slow: { label: 'Медленный монтаж', cut: '8–16 секунд; оставляй воздух, паузы и длинные взгляды.' },
    },
    transitions: [
      ['Cut on Beat', 'Удар музыки → жёсткая смена плана.', 'Для fast/action'],
      ['Match Cut', 'Сопоставить форму, движение или позу двух сцен.', 'Для medium/cinematic'],
      ['Whip Pan', 'Скрыть монтаж быстрым движением камеры.', 'Для action'],
      ['Dip to Black', 'Короткий уход в чёрный перед новым смысловым блоком.', 'Для dark/drama'],
      ['J-Cut', 'Звук следующего кадра появляется до изображения.', 'Для dialogue/drama'],
      ['L-Cut', 'Изображение меняется, а предыдущая реплика продолжается.', 'Для emotion/dialogue'],
      ['Speed Ramp', 'Короткое ускорение → нормальная скорость в точке удара.', 'Для action'],
      ['Match Motion', 'Следующий кадр продолжает направление движения.', 'Для fast'],
    ],
    effects: [
      ['Film Grain', 'Очень лёгкое зерно для единого кинематографичного слоя.', 'cinematic'],
      ['Vignette', 'Мягкое затемнение краёв для направления взгляда.', 'dark'],
      ['Motion Blur', 'Аккуратный blur на быстрых движениях и переходах.', 'action'],
      ['Glow', 'Тонкое свечение только для светлых акцентов и огня.', 'epic'],
      ['Directional Shake', 'Короткая вибрация на impact; не держать постоянно.', 'action'],
      ['Selective Desaturation', 'Убрать часть цвета в драматических моментах.', 'drama'],
      ['Letterbox', 'Единый cinematic crop на всём ролике, а не только в одном кадре.', 'cinematic'],
      ['Light Leak', 'Редкий мягкий переход между эмоциональными фрагментами.', 'romance'],
    ],
    checklist: [
      'Все материалы реально найдены через ClipFender/YouTube.',
      'Первый кадр задаёт настроение без лишней экспозиции сюжета.',
      'Кульминация содержит самые пригодные для монтажа материалы.',
      'Нет случайных дублей одного и того же кадра.',
      'Переходы поддерживают ритм, а не заменяют монтаж.',
      'Диалоги не обрываются посередине без причины.',
      'Громкость музыки и оригинального звука сбалансирована.',
      'Финальный кадр имеет понятную точку завершения.',
      'YouTube-источник и права на используемые материалы проверены.',
      'Экспорт проверен на телефоне и десктопе.',
    ],
  };

  function buildWorkbench() {
    const host = qs('.cf-ideas-main') || qs('main');
    if (!host || qs('#cfStage10Workbench')) return;

    const panel = document.createElement('section');
    panel.id = 'cfStage10Workbench';
    panel.className = 'cf10-workbench';
    panel.innerHTML = `
      <div class="cf10-workbench__head">
        <div><span class="cf10-kicker">МОНТАЖНАЯ МАСТЕРСКАЯ · STAGE 10</span><h2>Собери идею эдита</h2></div>
        <span class="cf-new-meta">Сценарий + переходы + чеклист</span>
      </div>
      <div class="cf10-controls">
        <div class="cf10-control"><label for="cf10Character">Персонаж</label><input id="cf10Character" maxlength="120" placeholder="Например: Джон Сноу"></div>
        <div class="cf10-control"><label for="cf10Mood">Настроение</label><select id="cf10Mood"><option value="action">Экшн</option><option value="dark">Тёмное</option><option value="drama">Драма</option><option value="romance">Романтика</option><option value="emotional">Эмоциональное</option><option value="epic">Эпичное</option><option value="tension">Напряжение</option><option value="melancholy">Меланхолия</option></select></div>
        <div class="cf10-control"><label for="cf10Tempo">Темп</label><select id="cf10Tempo"><option value="fast">Быстрые кадры</option><option value="medium" selected>Средний темп</option><option value="slow">Медленный монтаж</option></select></div>
        <div class="cf10-control"><label for="cf10Music">Музыкальное направление</label><input id="cf10Music" maxlength="120" placeholder="Например: dark trailer / piano"></div>
      </div>
      <div class="cf10-button-row"><button type="button" class="is-gold" id="cf10Generate">СГЕНЕРИРОВАТЬ ПЛАН</button><a id="cf10SearchReal" href="/search?mode=idea">НАЙТИ РЕАЛЬНЫЕ СЦЕНЫ</a><button type="button" id="cf10Random">СЛУЧАЙНАЯ ИДЕЯ</button></div>
      <div id="cf10IdeaStatus" class="cf10-status" role="status" aria-live="polite">Заполни хотя бы персонажа или направление.</div>
      <div id="cf10Plan" class="cf10-generator-result" aria-live="polite"></div>
      <div class="cf10-bank">
        <div class="cf10-bank__group"><h3>БАНК ПЕРЕХОДОВ</h3><div class="cf10-chip-grid" id="cf10Transitions"></div></div>
        <div class="cf10-bank__group"><h3>БАНК ЭФФЕКТОВ</h3><div class="cf10-chip-grid" id="cf10Effects"></div></div>
      </div>
      <div class="cf10-checklist">
        <div class="cf10-workbench__head"><div><span class="cf10-kicker">КОНТРОЛЬНЫЙ СПИСОК</span><h3 style="margin:5px 0 0;color:#dccba9;font:600 18px Cinzel,serif">Перед экспортом</h3></div><span id="cf10ChecklistCount" class="cf-new-meta">0 / ${IDEA_DATA.checklist.length}</span></div>
        <div class="cf10-progress"><span id="cf10Progress"></span></div>
        <div class="cf10-checklist__grid" id="cf10Checklist"></div>
      </div>`;
    host.prepend(panel);
  }

  function renderBank() {
    const transitionHost = qs('#cf10Transitions');
    const effectHost = qs('#cf10Effects');
    if (!transitionHost || !effectHost) return;
    transitionHost.innerHTML = IDEA_DATA.transitions.map((item) => `<button class="cf10-chip" type="button" data-kind="transition" data-name="${esc(item[0])}" title="${esc(item[1])}">${esc(item[0])}</button>`).join('');
    effectHost.innerHTML = IDEA_DATA.effects.map((item) => `<button class="cf10-chip" type="button" data-kind="effect" data-name="${esc(item[0])}" title="${esc(item[1])}">${esc(item[0])}</button>`).join('');
    qsa('.cf10-chip').forEach((button) => button.addEventListener('click', () => button.classList.toggle('is-active')));
  }

  function renderChecklist() {
    const host = qs('#cf10Checklist');
    if (!host) return;
    const key = 'clipfender_stage10_checklist_v1';
    let state = {};
    try { state = JSON.parse(localStorage.getItem(key) || '{}'); } catch { state = {}; }
    host.innerHTML = IDEA_DATA.checklist.map((label, index) => `<label class="cf10-check"><input type="checkbox" data-index="${index}" ${state[index] ? 'checked' : ''}><span>${esc(label)}</span></label>`).join('');
    const refresh = () => {
      const boxes = qsa('input[type="checkbox"]', host);
      const done = boxes.filter((box) => box.checked).length;
      const percent = Math.round((done / boxes.length) * 100);
      qs('#cf10ChecklistCount').textContent = `${done} / ${boxes.length}`;
      qs('#cf10Progress').style.width = `${percent}%`;
      const next = {}; boxes.forEach((box) => { next[box.dataset.index] = box.checked; });
      try { localStorage.setItem(key, JSON.stringify(next)); } catch {}
    };
    qsa('input[type="checkbox"]', host).forEach((box) => box.addEventListener('change', refresh));
    refresh();
  }

  function buildPlan(character, moodKey, tempoKey, music) {
    const mood = IDEA_DATA.moods[moodKey] || IDEA_DATA.moods.action;
    const tempo = IDEA_DATA.tempos[tempoKey] || IDEA_DATA.tempos.medium;
    const subject = character.trim() || 'персонажа';
    return [
      ['INTRO', `${subject}: холодный вход`, mood.intro, `${tempo.cut} Музыка: ${music || 'атмосферный intro'}.`],
      ['BUILD-UP', 'Первые повторы и нарастание', `Чередуй крупный план, действие и реакцию ${subject}. Добавляй движение, но сохраняй читаемость.`, `Переход: ${pickTransition(moodKey, tempoKey)}.`],
      ['CLIMAX', 'Главный удар', mood.climax, `Эффект: ${pickEffect(moodKey)}. Музыкальный акцент: ${music || 'главный удар композиции'}.`],
      ['OUTRO', 'После кульминации', `Дай один чистый эмоциональный кадр ${subject}, затем оставь короткий визуальный хвост и точку завершения.`, `Переход на выходе: ${pickExitTransition(moodKey)}.`],
    ];
  }

  function pickTransition(mood, tempo) {
    if (tempo === 'fast') return 'Cut on Beat';
    if (mood === 'dark') return 'Dip to Black';
    if (mood === 'romance') return 'Match Cut';
    return 'Match Motion';
  }

  function pickEffect(mood) {
    if (mood === 'dark') return 'Vignette';
    if (mood === 'action') return 'Motion Blur';
    if (mood === 'epic') return 'Glow';
    if (mood === 'romance') return 'Light Leak';
    return 'Film Grain';
  }

  function pickExitTransition(mood) {
    if (mood === 'drama' || mood === 'melancholy') return 'L-Cut';
    if (mood === 'dark') return 'Dip to Black';
    return 'Cut on Beat';
  }

  function renderPlan() {
    const character = String(qs('#cf10Character')?.value || '').trim();
    const moodKey = qs('#cf10Mood')?.value || 'action';
    const tempoKey = qs('#cf10Tempo')?.value || 'medium';
    const music = String(qs('#cf10Music')?.value || '').trim();
    const plan = buildPlan(character, moodKey, tempoKey, music);
    const host = qs('#cf10Plan');
    if (!host) return;
    host.innerHTML = plan.map((beat) => `<article class="cf10-beat"><strong>${esc(beat[0])}</strong><h3>${esc(beat[1])}</h3><p>${esc(beat[2])}</p><small>${esc(beat[3])}</small></article>`).join('');
    const params = new URLSearchParams({mode:'idea', mood:moodKey, tempo:tempoKey});
    if (character) params.set('q', character);
    if (music) params.set('music', music);
    const search = qs('#cf10SearchReal');
    if (search) search.href = `/search?${params.toString()}`;
    const status = qs('#cf10IdeaStatus');
    if (status) {
      status.dataset.kind = character || music ? 'ok' : '';
      status.textContent = character || music ? `План готов: ${IDEA_DATA.moods[moodKey].label} · ${IDEA_DATA.tempos[tempoKey].label}. Реальные сцены ищи кнопкой выше.` : 'План создан как универсальный шаблон. Для персонального сценария укажи персонажа или музыкальное направление.';
    }
  }

  function randomize() {
    const characters = ['Джон Сноу','Джейми Ланнистер','Дейенерис Таргариен','Тирион Ланнистер','Арья Старк','Серсея Ланнистер'];
    const moods = Object.keys(IDEA_DATA.moods);
    const tempos = Object.keys(IDEA_DATA.tempos);
    qs('#cf10Character').value = characters[Math.floor(Math.random() * characters.length)];
    qs('#cf10Mood').value = moods[Math.floor(Math.random() * moods.length)];
    qs('#cf10Tempo').value = tempos[Math.floor(Math.random() * tempos.length)];
    qs('#cf10Music').value = ['dark trailer','cinematic strings','piano + ambience','percussion + impact'][Math.floor(Math.random() * 4)];
    renderPlan();
  }

  function init() {
    if (!document.querySelector('.cf-ideas-main')) return;
    buildWorkbench(); renderBank(); renderChecklist();
    qs('#cf10Generate')?.addEventListener('click', renderPlan);
    qs('#cf10Random')?.addEventListener('click', randomize);
    qsa('#cf10Character,#cf10Music').forEach((field) => field.addEventListener('keydown', (event) => { if (event.key === 'Enter') { event.preventDefault(); renderPlan(); } }));
    renderPlan();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true}); else init();
})();
