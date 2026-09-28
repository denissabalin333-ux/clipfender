/* ClipFender Stage 14 — real portrait loading diagnostics and safe failure state. */
(() => {
  'use strict';

  const CACHE_VERSION = '1520';

  const buildBustedSrc = (src) => {
    const value = String(src || '').trim();
    if (!value) return '';
    return value.includes('?') ? `${value}&v=${CACHE_VERSION}` : `${value}?v=${CACHE_VERSION}`;
  };

  const showState = (shell, state, text) => {
    if (!shell) return;
    const status = shell.querySelector('.cf14-portrait-status');
    if (!status) return;
    const textNode = status.querySelector('.cf14-portrait-status__text');
    if (textNode) textNode.textContent = text;
    status.hidden = state === 'ready';
    status.classList.toggle('is-error', state === 'error');
    shell.classList.toggle('is-loading', state === 'loading');
    shell.classList.toggle('is-ready', state === 'ready');
  };

  const decorate = (shell) => {
    const img = shell?.querySelector('img[data-portrait-source], img[data-character-image]');
    if (!img || img.dataset.cf14Ready) return;
    img.dataset.cf14Ready = '1';

    const source = img.dataset.portraitSource || img.dataset.characterImage || img.getAttribute('src') || '';
    img.dataset.portraitSource = source;
    showState(shell, 'loading', 'ЗАГРУЗКА ПОРТРЕТА');

    const markReady = () => {
      if (img.naturalWidth > 0) {
        showState(shell, 'ready', '');
        img.removeAttribute('aria-busy');
      } else {
        markError();
      }
    };

    const markError = () => {
      img.removeAttribute('aria-busy');
      img.classList.add('is-broken');
      showState(shell, 'error', 'ПОРТРЕТ НЕДОСТУПЕН');
    };

    img.addEventListener('load', markReady, { once: true });
    img.addEventListener('error', markError, { once: true });
    img.setAttribute('aria-busy', 'true');

    const current = img.getAttribute('src') || '';
    const busted = buildBustedSrc(source);
    if (busted && current !== busted) img.src = busted;

    if (img.complete) {
      if (img.naturalWidth > 0) markReady();
      else if (current) markError();
    }
  };

  const boot = () => {
    document.querySelectorAll('.cf14-portrait-shell, .cf10-character-art').forEach(decorate);
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
