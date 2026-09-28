(() => {
  'use strict';
  const enabledMeta = document.querySelector('meta[name="cf-analytics-enabled"]');
  const domainMeta = document.querySelector('meta[name="cf-plausible-domain"]');
  const enabled = enabledMeta?.content === '1';
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
  }
  if (!enabled || localStorage.getItem('cf.analytics-consent') === 'granted') {
    if (enabled && localStorage.getItem('cf.analytics-consent') === 'granted') loadAnalytics();
    return;
  }
  const box = document.createElement('aside');
  box.className = 'cf7-cookie';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-label', 'Настройки аналитики');
  box.innerHTML = '<p>ClipFender может использовать необязательную privacy-friendly аналитику для оценки посещаемости. Она не включается без вашего согласия.</p><div class="cf7-cookie__actions"><a href="/privacy">Подробнее</a><button type="button" data-consent="decline">Не сейчас</button><button type="button" class="is-primary" data-consent="accept">Разрешить</button></div>';
  document.body.appendChild(box);
  box.addEventListener('click', (event) => {
    const action = event.target.closest('[data-consent]')?.dataset.consent;
    if (!action) return;
    localStorage.setItem('cf.analytics-consent', action === 'accept' ? 'granted' : 'denied');
    box.remove();
    if (action === 'accept') loadAnalytics();
  });
  function loadAnalytics() {
    if (document.querySelector('script[data-cf-plausible]')) return;
    const scriptUrl = document.querySelector('meta[name="cf-plausible-script"]')?.content || 'https://plausible.io/js/script.js';
    const domain = domainMeta?.content;
    if (!domain) return;
    const script = document.createElement('script');
    script.defer = true;
    script.dataset.cfPlausible = '1';
    script.dataset.domain = domain;
    script.src = scriptUrl;
    document.head.appendChild(script);
  }
})();
