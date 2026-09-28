/* ClipFender Stage 5 — atmosphere, motion, live suggestions and media polish. */
(() => {
  'use strict';

  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  const doc = document;
  const html = doc.documentElement;

  const qs = (selector, root = doc) => root.querySelector(selector);
  const qsa = (selector, root = doc) => [...root.querySelectorAll(selector)];

  function persistTheme(theme) {
    try { localStorage.setItem('clipfender_theme', theme); } catch (_) {}
  }

  function loadTheme() {
    let stored = '';
    try { stored = localStorage.getItem('clipfender_theme') || ''; } catch (_) {}
    if (stored === 'light') html.dataset.cfTheme = 'light';
    else delete html.dataset.cfTheme;
    return stored === 'light';
  }

  function createThemeToggle() {
    const host = qs('.cf2-header__actions');
    if (!host || qs('[data-cf-theme-toggle]', host)) return;

    const button = doc.createElement('button');
    button.type = 'button';
    button.className = 'cf5-theme-toggle';
    button.dataset.cfThemeToggle = '1';
    button.setAttribute('aria-label', 'Переключить тему');
    button.setAttribute('aria-pressed', String(html.dataset.cfTheme === 'light'));
    button.dataset.cfTooltip = 'Сменить тему';

    const sync = () => {
      const light = html.dataset.cfTheme === 'light';
      button.textContent = light ? '☾' : '☼';
      button.setAttribute('aria-pressed', String(light));
      button.setAttribute('aria-label', light ? 'Включить тёмную тему' : 'Включить светлую тему');
      button.dataset.cfTooltip = light ? 'Тёмная тема' : 'Светлая тема';
    };

    button.addEventListener('click', () => {
      const light = html.dataset.cfTheme === 'light';
      if (light) delete html.dataset.cfTheme;
      else html.dataset.cfTheme = 'light';
      persistTheme(light ? 'dark' : 'light');
      sync();
      window.showToast?.(light ? 'Тёмная тема включена.' : 'Светлая тема включена.', 'info');
    });

    host.insertBefore(button, qs('.cf2-mobile-toggle', host) || null);
    sync();
  }

  function createAtmosphere() {
    if (doc.querySelector('.cf5-atmosphere-canvas') || document.body.classList.contains('page-light')) return;

    const grain = doc.createElement('div');
    grain.className = 'cf5-grain';
    grain.setAttribute('aria-hidden', 'true');
    doc.body.appendChild(grain);

    const canvas = doc.createElement('canvas');
    canvas.className = 'cf5-atmosphere-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    doc.body.appendChild(canvas);
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const particles = [];
    let width = 1;
    let height = 1;
    let dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    let rafId = 0;
    let last = performance.now();

    const makeParticle = () => ({
      x: Math.random(),
      y: Math.random() * 1.05,
      size: .55 + Math.random() * 1.8,
      speed: .006 + Math.random() * .012,
      drift: (Math.random() - .5) * .0025,
      alpha: .12 + Math.random() * .36,
      phase: Math.random() * Math.PI * 2,
      warm: Math.random() > .18,
    });

    const targetCount = () => width < 700 ? 25 : width < 1100 ? 38 : 52;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      dpr = Math.min(window.devicePixelRatio || 1, 1.75);
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = targetCount();
      while (particles.length < count) particles.push(makeParticle());
      if (particles.length > count) particles.length = count;
    };

    resize();
    window.addEventListener('resize', resize, { passive: true });

    const drawStatic = () => {
      ctx.clearRect(0, 0, width, height);
      for (const p of particles) {
        const px = p.x * width;
        const py = p.y * height;
        ctx.beginPath();
        ctx.fillStyle = p.warm ? `rgba(224,184,106,${p.alpha * .55})` : `rgba(190,190,190,${p.alpha * .18})`;
        ctx.arc(px, py, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    const frame = (now) => {
      const dt = Math.min(48, now - last);
      last = now;
      ctx.clearRect(0, 0, width, height);
      for (const p of particles) {
        p.y -= p.speed * dt;
        p.x += p.drift * dt;
        p.phase += .0012 * dt;
        if (p.y < -.04) {
          p.y = 1.03;
          p.x = Math.random();
        }
        if (p.x < -.03) p.x = 1.03;
        if (p.x > 1.03) p.x = -.03;
        const pulse = .72 + Math.sin(p.phase) * .22;
        ctx.beginPath();
        ctx.fillStyle = p.warm
          ? `rgba(235,201,133,${p.alpha * pulse})`
          : `rgba(194,194,194,${p.alpha * pulse * .22})`;
        ctx.arc(p.x * width, p.y * height, p.size, 0, Math.PI * 2);
        ctx.fill();
      }
      rafId = requestAnimationFrame(frame);
    };

    if (!reduced) {
      rafId = requestAnimationFrame(frame);
      window.addEventListener('pagehide', () => cancelAnimationFrame(rafId), { once: true });
    } else {
      drawStatic();
    }
  }

  function setupReveal() {
    const candidates = qsa([
      'main > section',
      'main > .cf-new-page > section',
      '.home-stage3__feature',
      '.home-stage3__legend-panel',
      '.video-card',
      '.character-card-rich',
      '.service-card-rich',
      '.work-card-rich',
      '.idea-card',
      '.help-tool-card',
      '.project-card-large',
      '.featured-project-rich',
      '.faq-item-rich',
      '.contact-box',
      '.auth-card'
    ].join(','));

    if (!candidates.length) return;

    if (reduced || !('IntersectionObserver' in window)) {
      candidates.forEach(el => el.classList.add('cf5-reveal', 'is-visible'));
      return;
    }

    const unique = [...new Set(candidates)];
    unique.forEach((el, index) => {
      if (el.dataset.cf5RevealDone) return;
      el.dataset.cf5RevealDone = '1';
      el.classList.add('cf5-reveal');
      el.dataset.cf5Delay = String(index % 4);
    });

    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: .10, rootMargin: '0px 0px -7% 0px' });

    unique.forEach(el => observer.observe(el));
  }

  function setupParallax() {
    if (reduced) return;

    const hero = qs('.home-stage3, .home-hero');
    if (!hero) return;

    const scene = qs('[data-parallax="scene"], .hero-art-left', hero);
    const fog = qs('[data-parallax="fog"], .hero-vignette', hero);
    const far = qs('.hero-art-right', hero);
    if (!scene && !fog && !far) return;

    let rafId = 0;
    let px = 0;
    let py = 0;
    let sy = window.scrollY || 0;

    const render = () => {
      rafId = 0;
      const scroll = Math.min(180, sy * .05);
      if (scene) scene.style.transform = `translate3d(${px * -0.55}px, ${py * -0.32 + scroll}px, 0) scale(1.025)`;
      if (far) far.style.transform = `translate3d(${px * 0.22}px, ${py * 0.12 + scroll * .35}px, 0) scale(1.02)`;
      if (fog) fog.style.transform = `translate3d(${px * 0.10}px, ${py * 0.06 + scroll * .16}px, 0)`;
    };

    const schedule = () => {
      if (!rafId) rafId = requestAnimationFrame(render);
    };

    hero.addEventListener('pointermove', event => {
      const rect = hero.getBoundingClientRect();
      px = (event.clientX - rect.left - rect.width / 2) / Math.max(1, rect.width) * 18;
      py = (event.clientY - rect.top - rect.height / 2) / Math.max(1, rect.height) * 14;
      schedule();
    }, { passive: true });

    hero.addEventListener('pointerleave', () => {
      px = 0;
      py = 0;
      schedule();
    }, { passive: true });

    window.addEventListener('scroll', () => {
      sy = window.scrollY || 0;
      schedule();
    }, { passive: true });

    schedule();
  }

  const suggestions = [
    ['Джон Сноу', 'персонаж'],
    ['Дейенерис Таргариен', 'персонаж'],
    ['Джейми Ланнистер', 'персонаж'],
    ['Арья Старк', 'персонаж'],
    ['Тирион Ланнистер', 'персонаж'],
    ['Серсея Ланнистер', 'персонаж'],
    ['Битва', 'сцена'],
    ['Трон', 'сцена'],
    ['Cinematic', 'стиль'],
    ['Emotional', 'стиль']
  ];

  function setupLiveSearch() {
    const input = qs('#homeStage3Query, #heroQuery');
    const form = input?.closest('form');
    if (!input || !form || form.dataset.cf5Ready) return;
    form.dataset.cf5Ready = '1';
    form.style.position = 'relative';

    const panel = doc.createElement('div');
    panel.className = 'cf5-suggestions';
    panel.hidden = true;
    panel.setAttribute('role', 'listbox');
    form.appendChild(panel);

    let activeIndex = -1;

    const close = () => {
      panel.hidden = true;
      activeIndex = -1;
      qsa('[role="option"]', panel).forEach(item => item.setAttribute('aria-selected', 'false'));
    };

    const render = () => {
      const query = input.value.trim().toLowerCase();
      const matches = suggestions.filter(([label]) => !query || label.toLowerCase().includes(query)).slice(0, 6);
      if (!matches.length) {
        close();
        return;
      }
      panel.innerHTML = matches.map(([label, meta]) => `
        <button type="button" class="cf5-suggestions__item" role="option" data-cf5-query="${label.replaceAll('"', '&quot;')}">
          ${label}
          <span class="cf5-suggestions__meta">${meta}</span>
        </button>
      `).join('');
      panel.hidden = false;
      activeIndex = -1;
      qsa('.cf5-suggestions__item', panel).forEach(item => item.addEventListener('click', () => {
        input.value = item.dataset.cf5Query || '';
        close();
        input.focus();
      }));
    };

    input.addEventListener('focus', render);
    input.addEventListener('input', render);
    input.addEventListener('keydown', event => {
      if (panel.hidden) return;
      const items = qsa('.cf5-suggestions__item', panel);
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        activeIndex = Math.min(items.length - 1, activeIndex + 1);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        activeIndex = Math.max(0, activeIndex - 1);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      } else if (event.key === 'Enter' && activeIndex >= 0) {
        event.preventDefault();
        items[activeIndex]?.click();
        return;
      } else return;
      items.forEach((item, index) => item.setAttribute('aria-selected', String(index === activeIndex)));
    });

    doc.addEventListener('pointerdown', event => {
      if (!form.contains(event.target)) close();
    });

    if (!form.querySelector('.cf5-random-button')) {
      const random = doc.createElement('button');
      random.type = 'button';
      random.className = 'cf5-random-button';
      random.textContent = '⚔ СЛУЧАЙНЫЙ РОЛИК ДЛЯ ЭДИТА';
      random.dataset.cfTooltip = 'Открыть случайный запрос в архиве';
      random.addEventListener('click', () => {
        const pool = suggestions.filter(([_, meta]) => meta === 'персонаж').map(([label]) => label);
        const query = pool[Math.floor(Math.random() * pool.length)] || 'битва';
        window.location.href = `/search?q=${encodeURIComponent(query)}`;
      });
      form.appendChild(random);
    }
  }

  function addPopularToday() {
    if (!qs('.home-stage3__below') || qs('#cf5PopularToday')) return;
    const section = doc.createElement('section');
    section.className = 'cf5-popular';
    section.id = 'cf5PopularToday';
    section.setAttribute('aria-labelledby', 'cf5PopularTitle');
    const popular = [
      ['01', 'ДЖОН СНОУ', 'Север · эмоции'],
      ['02', 'ДЕЙЕНЕРИС', 'Драконы · эпика'],
      ['03', 'АРЬЯ СТАРК', 'Бои · динамика'],
      ['04', 'ДЖЕЙМИ ЛАННИСТЕР', 'Диалоги · драма'],
      ['05', 'ТИРИОН', 'Диалоги · ирония'],
      ['06', 'СЕРСЕЯ', 'Трон · напряжение']
    ];
    section.innerHTML = `
      <header class="cf5-popular__header">
        <div>
          <span class="cf5-popular__eyebrow">АРХИВ · ПОПУЛЯРНОЕ СЕГОДНЯ</span>
          <h2 id="cf5PopularTitle" class="cf5-popular__title">Кадры, с которых часто начинают эдит</h2>
        </div>
        <p class="cf5-popular__copy">Готовые входы в поиск: выбирай персонажа и переходи прямо к сценам, фильтрам и результатам YouTube.</p>
      </header>
      <div class="cf5-popular__grid">
        ${popular.map(([rank, name, meta]) => `
          <a class="cf5-popular__item" href="/search?q=${encodeURIComponent(name)}">
            <span class="cf5-popular__rank">${rank}</span>
            <span class="cf5-popular__name">${name}</span>
            <span class="cf5-popular__meta">${meta}</span>
          </a>`).join('')}
      </div>
    `;
    qs('.home-stage3__below')?.insertAdjacentElement('afterend', section);
  }

  function animateCounters() {
    const counters = qsa('.home-stage3__seal-item strong');
    if (!counters.length || reduced) return;
    counters.forEach(el => {
      if (el.dataset.cf5CounterDone) return;
      const original = el.textContent.trim();
      const match = original.match(/([\d.,]+)(.*)/);
      if (!match) return;
      const target = Number(match[1].replaceAll(',', ''));
      const suffix = match[2];
      if (!Number.isFinite(target)) return;
      el.dataset.cf5CounterDone = '1';
      const start = performance.now();
      const duration = 900;
      const tick = now => {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = Math.round(target * eased);
        el.textContent = `${value.toLocaleString('ru-RU')}${suffix}`;
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }

  function createSkeleton(container, count = 6) {
    if (!container || container.querySelector('.cf5-skeleton-grid')) return;
    const grid = doc.createElement('div');
    grid.className = 'cf5-skeleton-grid';
    grid.setAttribute('aria-label', 'Загрузка результатов');
    grid.setAttribute('aria-busy', 'true');
    grid.innerHTML = Array.from({ length: count }, () => `
      <div class="cf5-skeleton-card">
        <div class="cf5-skeleton-card__thumb"></div>
        <div class="cf5-skeleton-card__body">
          <div class="cf5-skeleton-card__line"></div>
          <div class="cf5-skeleton-card__line"></div>
          <div class="cf5-skeleton-card__line"></div>
        </div>
      </div>
    `).join('');
    container.replaceChildren(grid);
  }

  function setupArchivePolish() {
    const videos = qs('#videos');
    const searchButton = qs('#searchButton');
    if (!videos || !searchButton) return;

    const addCopyButton = card => {
      if (card.querySelector('[data-cf5-copy]')) return;
      const actions = qs('.actions', card);
      const watch = qs('.watch-button', card);
      if (!actions || !watch) return;
      const button = doc.createElement('button');
      button.type = 'button';
      button.className = 'cf5-copy-button';
      button.dataset.cf5Copy = '1';
      button.dataset.cfTooltip = 'Скопировать ссылку';
      button.textContent = 'Ссылка';
      button.addEventListener('click', async () => {
        const url = watch.href;
        try {
          if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(url);
          else {
            const helper = doc.createElement('textarea');
            helper.value = url;
            helper.style.position = 'fixed';
            helper.style.opacity = '0';
            doc.body.appendChild(helper);
            helper.select();
            doc.execCommand('copy');
            helper.remove();
          }
          window.showToast?.('Ссылка скопирована.', 'success');
        } catch (_) {
          window.showToast?.('Не удалось скопировать ссылку.', 'error');
        }
      });
      actions.appendChild(button);
    };

    const cardObserver = new MutationObserver(() => {
      qsa('.video-card', videos).forEach(addCopyButton);
    });
    cardObserver.observe(videos, { childList: true, subtree: true });
    qsa('.video-card', videos).forEach(addCopyButton);

    const loadingObserver = new MutationObserver(() => {
      if (searchButton.disabled && !videos.querySelector('.cf5-skeleton-grid')) createSkeleton(videos, window.innerWidth < 720 ? 3 : 6);
    });
    loadingObserver.observe(searchButton, { attributes: true, attributeFilter: ['disabled'] });

    const modal = qs('#modal');
    const modalBody = qs('#modalBody');
    if (!modal || !modalBody) return;

    const injectPlayerTrigger = () => {
      if (!modal.classList.contains('active') || modalBody.querySelector('[data-cf5-player-trigger]')) return;
      const link = qs('a[href*="youtube.com/watch"], a[href*="youtu.be/"]', modalBody);
      if (!link) return;
      const match = link.href.match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
      if (!match) return;
      const trigger = doc.createElement('button');
      trigger.type = 'button';
      trigger.className = 'cf5-player-trigger';
      trigger.dataset.cf5PlayerTrigger = '1';
      trigger.dataset.videoId = match[1];
      trigger.dataset.cfTooltip = 'Загрузить официальный YouTube-плеер';
      trigger.textContent = '▶ В ПЛЕЕРЕ';
      trigger.style.marginTop = '14px';
      trigger.addEventListener('click', () => {
        if (modalBody.querySelector('.cf5-player-shell')) return;
        const shell = doc.createElement('div');
        shell.className = 'cf5-player-shell';
        shell.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${match[1]}?autoplay=1&rel=0&modestbranding=1" title="YouTube видео" loading="eager" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>`;
        trigger.replaceWith(shell);
      });
      link.insertAdjacentElement('afterend', trigger);
    };

    const modalObserver = new MutationObserver(injectPlayerTrigger);
    modalObserver.observe(modalBody, { childList: true, subtree: true });
    injectPlayerTrigger();
  }

  function setupPageMicrocopy() {
    qsa('[title]').forEach(el => {
      if (el.dataset.cfTooltip || !el.title || !['BUTTON', 'A'].includes(el.tagName)) return;
      const title = el.title.trim();
      if (!title) return;
      el.dataset.cfTooltip = title;
    });
  }

  function boot() {
    loadTheme();
    createThemeToggle();
    createAtmosphere();
    setupReveal();
    setupParallax();
    setupLiveSearch();
    addPopularToday();
    animateCounters();
    setupArchivePolish();
    setupPageMicrocopy();
    window.CFStage5 = {
      createSkeleton,
      syncTheme: loadTheme
    };
  }

  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
