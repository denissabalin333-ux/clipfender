(() => {
  'use strict';

  const path = location.pathname.replace(/\/$/, '') || '/';
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

  const nav = document.getElementById('navLinks');
  const mobileButton = document.querySelector('.cf2-mobile-toggle');
  const mobileBackdrop = document.querySelector('[data-mobile-backdrop]');

  const normalizeRoute = (href = '') => {
    const clean = href.split('?')[0].split('#')[0] || '/';
    return clean === '' ? '/' : clean.replace(/\/$/, '') || '/';
  };

  // One navigation state manager. It never blocks normal browser navigation.
  nav?.querySelectorAll('a[href]').forEach((a) => {
    a.classList.toggle('active', normalizeRoute(a.getAttribute('href')) === path);
    a.addEventListener('click', () => closeMenu(), { passive: true });
  });

  function closeMenu() {
    if (!nav) return;
    nav.classList.remove('open');
    mobileButton?.setAttribute('aria-expanded', 'false');
    mobileButton?.setAttribute('aria-label', 'Открыть меню');
    mobileBackdrop?.setAttribute('aria-hidden', 'true');
    mobileBackdrop?.classList.remove('is-open');
    document.body.classList.remove('menu-open');
  }

  function setMenu(open) {
    if (!nav) return;
    nav.classList.toggle('open', open);
    mobileButton?.setAttribute('aria-expanded', String(open));
    mobileButton?.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    mobileBackdrop?.setAttribute('aria-hidden', String(!open));
    mobileBackdrop?.classList.toggle('is-open', open);
    document.body.classList.toggle('menu-open', open);
  }

  mobileBackdrop?.addEventListener('click', () => closeMenu(), { passive: true });
  window.addEventListener('resize', () => { if (window.innerWidth > 820) closeMenu(); }, { passive: true });
  window.toggleMobileMenu = () => setMenu(!nav?.classList.contains('open'));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeMenu();
      window.closeLore?.();
    }
  });

  // Accessible toast helper, shared by local actions.
  if (!window.showToast) {
    window.showToast = (message, type = 'info') => {
      let toast = document.getElementById('toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        document.body.appendChild(toast);
      }
      toast.dataset.type = type;
      toast.textContent = message;
      toast.classList.add('show');
      window.clearTimeout(window.__cf6ToastTimer);
      window.__cf6ToastTimer = window.setTimeout(() => toast.classList.remove('show'), 2800);
    };
  }

  // Home search keeps existing archive/API workflow.
  const homeForm = document.getElementById('homeStage3Search');
  const homeInput = document.getElementById('homeStage3Query');
  const goArchive = (value) => {
    const q = String(value || '').trim();
    location.href = '/search' + (q ? `?q=${encodeURIComponent(q)}` : '');
  };
  homeForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    goArchive(homeInput?.value);
  });
  window.goToArchive = () => goArchive(document.getElementById('heroQuery')?.value || homeInput?.value || '');

  // Character catalogue filter + local favorites.
  const charInput = document.getElementById('cfCharacterSearch');
  const charMeta = document.getElementById('cfCharacterSearchMeta');
  const charCards = [...document.querySelectorAll('[data-character-name]')];
  let charFavs = [];
  try { charFavs = JSON.parse(localStorage.getItem('clipfender_character_favorites') || '[]'); } catch {}

  function applyCharacterSearch() {
    const query = String(charInput?.value || '').trim().toLowerCase();
    let visible = 0;
    charCards.forEach((card) => {
      const haystack = `${card.dataset.characterName || ''} ${card.dataset.characterWorld || ''} ${card.textContent || ''}`.toLowerCase();
      const show = !query || haystack.includes(query);
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (charMeta) charMeta.textContent = query ? `Найдено персонажей: ${visible}` : `В каталоге: ${visible}`;
  }
  charInput?.addEventListener('input', applyCharacterSearch);
  charCards.forEach((card) => {
    const button = card.querySelector('[data-character-favorite]');
    if (!button) return;
    const name = button.dataset.characterFavorite;
    const sync = () => {
      const active = charFavs.includes(name);
      button.classList.toggle('is-active', active);
      button.textContent = active ? '★ В ИЗБРАННОМ' : '☆ В ИЗБРАННОЕ';
    };
    sync();
    button.addEventListener('click', () => {
      const index = charFavs.indexOf(name);
      if (index >= 0) charFavs.splice(index, 1); else charFavs.push(name);
      localStorage.setItem('clipfender_character_favorites', JSON.stringify(charFavs));
      sync();
      window.showToast(activeMessage(name, index < 0), 'success');
    });
  });
  applyCharacterSearch();

  function activeMessage(name, added) {
    return added ? `${name}: добавлено в избранное.` : `${name}: удалено из избранного.`;
  }

  // Character finder: local profile + archive handoff.
  const profiles = {
    'джон сноу': ['Джон Сноу','СТАРК','Игра престолов','/static/assets/reference/final/jon-hq.webp'],
    'джейми ланнистер': ['Джейми Ланнистер','ЛАННИСТЕР','Игра престолов','/static/assets/reference/final/jaime-hq.webp'],
    'дейенерис': ['Дейенерис Таргариен','ТАРГАРИЕН','Игра престолов','/static/assets/reference/final/daenerys-hq.webp'],
    'дейенерис таргариен': ['Дейенерис Таргариен','ТАРГАРИЕН','Игра престолов','/static/assets/reference/final/daenerys-hq.webp'],
    'тирион': ['Тирион Ланнистер','ЛАННИСТЕР','Игра престолов','/static/assets/reference/final/tyrion-hq.webp'],
    'тирион ланнистер': ['Тирион Ланнистер','ЛАННИСТЕР','Игра престолов','/static/assets/reference/final/tyrion-hq.webp'],
    'арья': ['Арья Старк','СТАРК','Игра престолов','/static/assets/reference/final/arya-hq.webp'],
    'арья старк': ['Арья Старк','СТАРК','Игра престолов','/static/assets/reference/final/arya-hq.webp'],
    'серсея': ['Серсея Ланнистер','ЛАННИСТЕР','Игра престолов','/static/assets/reference/final/cersei-hq.webp']
  };

  const characterForm = document.getElementById('characterSearchForm');
  characterForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    const input = document.getElementById('characterSearchInput');
    const query = String(input?.value || '').trim();
    if (!query) { input?.focus(); return; }
    const key = query.toLowerCase().replace(/ё/g, 'е');
    const profile = profiles[key] || Object.entries(profiles).find(([name]) => key.includes(name) || name.includes(key))?.[1];
    const cardHost = document.getElementById('characterSearchResult') || createProfileHost(characterForm);
    if (!profile) {
      cardHost.innerHTML = `<div class="cf-profile-result__empty"><b>ПЕРСОНАЖ НЕ НАЙДЕН В КАТАЛОГЕ</b><p>Запрос будет передан в рабочий архив материалов.</p><a class="btn" href="/archive?q=${encodeURIComponent(query)}">НАЙТИ СЦЕНЫ →</a></div>`;
      return;
    }
    const [name, house, world, image] = profile;
    cardHost.innerHTML = `<article class="cf-profile-result__card"><img src="${image}" alt="${name}"><div><span>${house} · ${world}</span><h2>${name}</h2><p>Профиль персонажа готов: переходи к сценам, истории и исходным материалам.</p><div class="cf-profile-result__actions"><a class="btn" href="/archive?q=${encodeURIComponent(name)}">НАЙТИ СЦЕНЫ →</a><button class="btn btn-gold" type="button" data-profile-lore>ИСТОРИЯ</button></div></div></article>`;
    cardHost.querySelector('[data-profile-lore]')?.addEventListener('click', () => window.showLore?.(name, `${name}. Мир: ${world}. Дом: ${house}. Используй профиль как точку входа в архив сцен, диалогов и персонажных моментов.`, house));
  });

  function createProfileHost(form) {
    const host = document.createElement('section');
    host.id = 'characterSearchResult';
    host.className = 'cf-profile-result';
    form.closest('.cf-search-card')?.appendChild(host);
    return host;
  }

  // Ideas search, categories, favorites. The page keeps its real archive handoff.
  const ideaInput = document.getElementById('cfIdeaSearch');
  const ideaCards = [...document.querySelectorAll('[data-idea-source]')];
  const ideaMeta = document.getElementById('cfIdeaMeta');
  let ideaFavs = [];
  try { ideaFavs = JSON.parse(localStorage.getItem('clipfender_idea_favorites') || '[]'); } catch {}

  function applyIdeas() {
    const query = String(ideaInput?.value || '').trim().toLowerCase();
    const active = document.querySelector('[data-idea-category-btn].is-active')?.dataset.ideaCategory || 'all';
    let visible = 0;
    ideaCards.forEach((card) => {
      const haystack = `${card.dataset.ideaSource || ''} ${card.dataset.ideaTitle || ''} ${card.dataset.ideaTags || ''} ${card.textContent || ''}`.toLowerCase();
      const categories = (card.dataset.ideaCategory || '').split(/\s+/);
      const show = (active === 'all' || categories.includes(active)) && (!query || haystack.includes(query));
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (ideaMeta) ideaMeta.textContent = `Найдено идей: ${visible}`;
    const empty = document.getElementById('cfIdeaEmpty');
    if (empty) {
      empty.hidden = visible > 0;
      const fallback = empty.querySelector('[data-idea-fallback]');
      const q = String(ideaInput?.value || '').trim();
      if (fallback) fallback.href = q ? `/archive?q=${encodeURIComponent(q + ' cinematic edit')}` : '/search';
    }
  }
  document.querySelectorAll('[data-idea-popular]').forEach((button) => {
    button.addEventListener('click', () => {
      if (ideaInput) { ideaInput.value = button.dataset.ideaPopular || ''; ideaInput.dispatchEvent(new Event('input', { bubbles: true })); ideaInput.focus(); }
    });
  });
  ideaInput?.addEventListener('input', applyIdeas);
  ideaInput?.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    const q = String(ideaInput.value || '').trim();
    if (q) location.href = `/archive?q=${encodeURIComponent(q + ' cinematic edit')}`;
  });
  document.querySelectorAll('[data-idea-category-btn]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-idea-category-btn]').forEach((b) => b.classList.remove('is-active'));
      button.classList.add('is-active');
      applyIdeas();
    });
  });
  document.querySelectorAll('[data-idea-favorite]').forEach((button) => {
    const id = button.dataset.ideaFavorite;
    const sync = () => {
      const active = ideaFavs.includes(id);
      button.classList.toggle('is-active', active);
      button.textContent = active ? '★ СОХРАНЕНО' : '☆ СОХРАНИТЬ';
    };
    sync();
    button.addEventListener('click', () => {
      const index = ideaFavs.indexOf(id);
      if (index >= 0) ideaFavs.splice(index, 1); else ideaFavs.push(id);
      localStorage.setItem('clipfender_idea_favorites', JSON.stringify(ideaFavs));
      sync();
      window.showToast(activeMessage(id, index < 0), 'success');
    });
  });
  applyIdeas();


  // Reusable lore modal fallback for pages that do not load site.js.
  window.showLore = window.showLore || ((title, body, house) => {
    let modal = document.getElementById('cf6-lore-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'cf6-lore-modal';
      modal.className = 'modal active';
      modal.innerHTML = `<div class="modal-content"><button class="modal-close" type="button" aria-label="Закрыть">×</button><div class="modal-title"></div><p class="cf6-lore-body"></p><div class="cf6-lore-house"></div></div>`;
      document.body.appendChild(modal);
      modal.addEventListener('click', (event) => { if (event.target === modal) modal.remove(); });
      modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
    } else {
      modal.classList.add('active');
    }
    modal.querySelector('.modal-title').textContent = title;
    modal.querySelector('.cf6-lore-body').textContent = body;
    modal.querySelector('.cf6-lore-house').textContent = house;
    modal.querySelector('.modal-close')?.focus();
  });
  window.characterSearch = window.characterSearch || ((name) => {
    location.href = `/archive?q=${encodeURIComponent(name)}`;
  });
  window.portfolioFilter = window.portfolioFilter || ((kind) => {
    document.querySelectorAll('[data-kind]').forEach((item) => { item.hidden = kind !== 'all' && item.dataset.kind !== kind; });
    document.querySelectorAll('[data-filter]').forEach((item) => item.classList.toggle('active', item.dataset.filter === kind));
  });
  window.faqToggle = window.faqToggle || ((button) => {
    const item = button.closest('.faq-item,.faq-item-rich');
    if (!item) return;
    const open = !item.classList.contains('open');
    item.classList.toggle('open', open);
    button.setAttribute('aria-expanded', String(open));
  });
  window.closeLore = window.closeLore || (() => document.getElementById('cf6-lore-modal')?.remove());

  // Existing local service checks remain functional.
  window.testHealth = async () => {
    try {
      const response = await fetch('/health', { headers: { Accept: 'application/json' } });
      const data = await response.json();
      if (!response.ok) throw new Error('HTTP ' + response.status);
      window.showToast(`Сервер: ${data.status || 'ok'}`, 'success');
    } catch {
      window.showToast('Сервер недоступен', 'error');
    }
  };
  window.testQuota = async () => {
    try {
      const response = await fetch('/api/quota', { headers: { Accept: 'application/json' } });
      const data = await response.json();
      if (!response.ok) throw new Error('HTTP ' + response.status);
      window.showToast(`Квота: осталось ${data.remaining ?? 0} из ${data.limit ?? 0}`, 'info');
    } catch {
      window.showToast('Не удалось получить квоту', 'error');
    }
  };

  // Hash links land below the fixed header without changing route behaviour.
  if (location.hash) {
    window.setTimeout(() => {
      const target = document.querySelector(location.hash);
      if (target) target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
    }, 120);
  }

  // Visual-only reveal; never intercepts navigation or forms.
  if (!reduced && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: .06 });
    document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-visible'));
  }

  // Small parallax on real artwork only; content never moves.
  if (!reduced) {
    document.querySelectorAll('.home-stage3').forEach((hero) => {
      const scene = hero.querySelector('.home-stage3__scene');
      if (!scene) return;
      let raf = 0;
      hero.addEventListener('pointermove', (event) => {
        const r = hero.getBoundingClientRect();
        const x = ((event.clientX - r.left) / r.width - .5) * 4;
        const y = ((event.clientY - r.top) / r.height - .5) * 2.5;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => { scene.style.transform = `scale(1.02) translate3d(${x}px,${y}px,0)`; });
      }, { passive: true });
      hero.addEventListener('pointerleave', () => { scene.style.transform = 'scale(1.02) translate3d(0,0,0)'; });
    });
  }
})();
