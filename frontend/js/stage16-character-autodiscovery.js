(() => {
  'use strict';

  const normalize = value => String(value || '').trim().toLocaleLowerCase('ru-RU');
  const readCookie = name => {
    const prefix = `${name}=`;
    const match = document.cookie.split(';').map(part => part.trim()).find(part => part.startsWith(prefix));
    return match ? decodeURIComponent(match.slice(prefix.length)) : '';
  };

  const ensureCharacter = async (name, {reloadOnSuccess = false, signal = undefined} = {}) => {
    const cleanName = String(name || '').trim().replace(/\s+/g, ' ');
    if (cleanName.length < 3 || cleanName.length > 80) return {ok: false, skipped: true};

    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    let token = readCookie('cf_csrf');
    if (!token) {
      try {
        const csrfResponse = await fetch('/api/auth/csrf', { credentials: 'same-origin', headers: { 'Accept': 'application/json' } });
        if (csrfResponse.ok) token = readCookie('cf_csrf');
      } catch (_) {}
    }
    if (token) headers['X-CSRF-Token'] = token;

    try {
      const response = await fetch('/api/characters/ensure', {
        method: 'POST',
        headers,
        credentials: 'same-origin',
        body: JSON.stringify({name: cleanName}),
        signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok && response.status !== 503) {
        return {ok: false, status: response.status, data};
      }
      if (data.status === 'ready' && data.character) {
        if (reloadOnSuccess) window.location.reload();
        return {ok: true, created: Boolean(data.created), data};
      }
      return {ok: false, status: response.status, data};
    } catch (error) {
      if (error?.name === 'AbortError') return {ok: false, timedOut: true};
      return {ok: false, error};
    }
  };

  const setupCharactersPage = () => {
    const root = document.getElementById('characterCatalog');
    const search = document.getElementById('cf12CharacterSearch');
    const meta = document.getElementById('cf12CharacterMeta');
    if (!root || !search) return;

    let timer = 0;
    let activeName = '';

    const localMatch = value => {
      const needle = normalize(value);
      if (!needle) return true;
      return Array.from(root.querySelectorAll('.cf12-character-card')).some(card => {
        const name = normalize(card.dataset.characterName);
        return name === needle || name.includes(needle);
      });
    };

    search.addEventListener('input', () => {
      window.clearTimeout(timer);
      const value = search.value.trim();
      if (value.length < 4 || localMatch(value)) return;
      const normalized = normalize(value);
      timer = window.setTimeout(async () => {
        if (normalize(search.value) !== normalized || activeName === normalized) return;
        activeName = normalized;
        if (meta) meta.textContent = `Ищем качественный портрет для «${value}»…`;
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 70000);
        const result = await ensureCharacter(value, {reloadOnSuccess: false, signal: controller.signal});
        window.clearTimeout(timeout);
        if (result.ok && result.created) {
          window.location.reload();
          return;
        }
        if (meta) meta.textContent = 'Нового персонажа пока не удалось добавить. Попробуй другое имя.';
        activeName = '';
      }, 900);
    });
  };

  const setupIdeaPage = () => {
    const form = document.getElementById('cf8SearchForm');
    const character = document.getElementById('cf8Character');
    const status = document.getElementById('cf8Status');
    if (!form || !character || form.dataset.cf16Discovery !== undefined) return;
    form.dataset.cf16Discovery = '1';

    let active = false;
    let ensured = new Set();

    form.addEventListener('submit', async event => {
      if (character.value.trim().length < 3 || active) return;
      const name = character.value.trim();
      const key = normalize(name);
      if (ensured.has(key)) return;
      active = true;
      const original = status?.textContent || '';
      if (status) status.textContent = `Проверяю каталог: готовлю качественный портрет «${name}»…`;
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 70000);
      const result = await ensureCharacter(name, {signal: controller.signal});
      window.clearTimeout(timeout);
      ensured.add(key);
      active = false;
      if (status) {
        if (result.ok && result.created) status.textContent = `Персонаж «${name}» добавлен в каталог. Продолжаю поиск материалов…`;
        else if (result.timedOut) status.textContent = `${original} Автодобавление портрета продолжается отдельно.`;
        else status.textContent = original;
      }
    }, true);
  };

  document.addEventListener('DOMContentLoaded', () => {
    setupCharactersPage();
    setupIdeaPage();
  });
})();
