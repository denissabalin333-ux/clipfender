(() => {
  'use strict';

  const SELECTORS = {
    login: '[data-cf-auth-login]',
    account: '[data-cf-account]',
    name: '[data-cf-account-name]',
    email: '[data-cf-account-email]',
    menu: '[data-cf-account-menu]',
    toggle: '[data-cf-account-toggle]',
    logout: '[data-cf-account-logout]',
  };

  const api = async (url, options = {}) => {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const data = await response.json();
        if (data?.detail) {
          detail = Array.isArray(data.detail)
            ? data.detail.map(item => item.msg || '').filter(Boolean).join('; ')
            : String(data.detail);
        }
      } catch (_) {
        // Keep HTTP status fallback.
      }

      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }

    return response.json();
  };

  const getCsrf = async () => {
    if (typeof window.ensureCsrfToken === 'function') {
      return window.ensureCsrfToken();
    }

    const response = await fetch('/api/auth/csrf', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });

    if (!response.ok) {
      throw new Error('Не удалось получить CSRF-токен');
    }

    const data = await response.json().catch(() => ({}));
    if (data?.token) return data.token;

    const raw = document.cookie
      .split('; ')
      .find(item => item.startsWith('cf_csrf='));

    return raw ? decodeURIComponent(raw.slice('cf_csrf='.length)) : '';
  };

  const setAuthenticatedState = (user) => {
    const login = document.querySelector(SELECTORS.login);
    const account = document.querySelector(SELECTORS.account);
    const name = document.querySelector(SELECTORS.name);
    const email = document.querySelector(SELECTORS.email);

    if (!login || !account) return;

    if (user) {
      login.hidden = true;
      account.hidden = false;

      if (name) {
        name.textContent = String(user.name || 'ПРОФИЛЬ');
      }

      if (email) {
        email.textContent = String(user.email || '');
      }

      document.documentElement.dataset.authenticated = '1';
      window.clipFenderUser = user;
      window.dispatchEvent(new CustomEvent('clipfender:auth-changed', {
        detail: { authenticated: true, user },
      }));
      return;
    }

    login.hidden = false;
    account.hidden = true;
    document.documentElement.dataset.authenticated = '0';
    window.clipFenderUser = null;

    window.dispatchEvent(new CustomEvent('clipfender:auth-changed', {
      detail: { authenticated: false, user: null },
    }));
  };

  const loadCurrentUser = async () => {
    try {
      const data = await api('/api/auth/me');
      const user = data?.authenticated ? data.user : null;
      setAuthenticatedState(user);
      return user;
    } catch (_) {
      setAuthenticatedState(null);
      return null;
    }
  };

  const closeMenu = () => {
    const menu = document.querySelector(SELECTORS.menu);
    const toggle = document.querySelector(SELECTORS.toggle);

    if (menu) menu.hidden = true;
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
  };

  const openOrCloseMenu = () => {
    const menu = document.querySelector(SELECTORS.menu);
    const toggle = document.querySelector(SELECTORS.toggle);

    if (!menu || !toggle) return;

    const nextOpen = menu.hidden;
    menu.hidden = !nextOpen;
    toggle.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
  };

  const logout = async () => {
    const button = document.querySelector(SELECTORS.logout);
    if (button) {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    }

    try {
      const token = await getCsrf();

      await api('/api/auth/logout', {
        method: 'POST',
        headers: {
          'X-CSRF-Token': token,
        },
      });

      closeMenu();
      setAuthenticatedState(null);

      window.dispatchEvent(new CustomEvent('clipfender:logged-out'));

      window.showToast?.('Вы вышли из аккаунта.', 'success');

      window.setTimeout(() => {
        window.location.href = '/';
      }, 300);
    } catch (error) {
      window.showToast?.(
        error.message || 'Не удалось выполнить выход.',
        'error'
      );
    } finally {
      if (button) {
        button.disabled = false;
        button.removeAttribute('aria-busy');
      }
    }
  };

  const init = () => {
    const login = document.querySelector(SELECTORS.login);
    const account = document.querySelector(SELECTORS.account);

    if (!login || !account) return;

    document.querySelector(SELECTORS.toggle)?.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      openOrCloseMenu();
    });

    document.querySelector(SELECTORS.logout)?.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      logout();
    });

    document.addEventListener('click', (event) => {
      const accountRoot = document.querySelector(SELECTORS.account);
      if (!accountRoot || accountRoot.hidden) return;

      if (!accountRoot.contains(event.target)) {
        closeMenu();
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeMenu();
    });

    window.addEventListener('clipfender:auth-refresh', loadCurrentUser);

    loadCurrentUser();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  window.clipFenderAuth = {
    refresh: loadCurrentUser,
    getUser: () => window.clipFenderUser || null,
  };
})();
