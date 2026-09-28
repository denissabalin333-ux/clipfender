(() => {
  'use strict';
  const form = document.getElementById('deleteAccountForm');
  if (!form) return;
  const status = document.getElementById('deleteAccountStatus');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const password = document.getElementById('deleteAccountPassword')?.value || '';
    if (!password) return;
    if (!window.confirm('Удалить аккаунт и всю библиотеку? Это действие необратимо.')) return;
    try {
      const csrfResponse = await fetch('/api/auth/csrf', { credentials: 'same-origin' });
      const csrfData = await csrfResponse.json();
      const token = csrfData?.token || document.cookie.split('; ').find(v => v.startsWith('cf_csrf='))?.split('=')[1];
      const response = await fetch('/api/auth/me', {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', ...(token ? { 'X-CSRF-Token': decodeURIComponent(token) } : {}) },
        body: JSON.stringify({ password })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Не удалось удалить аккаунт');
      status.textContent = 'Аккаунт удалён. Возвращаемся на главную…';
      setTimeout(() => { location.href = '/'; }, 700);
    } catch (error) {
      status.textContent = error.message || 'Не удалось удалить аккаунт';
    }
  });
})();
