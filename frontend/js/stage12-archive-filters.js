(() => {
  'use strict';

  const filters = document.getElementById('filters');
  if (!filters || typeof searchVideos !== 'function') return;

  let debounceTimer = null;
  let lastSignature = '';

  const filterIds = [
    'shorts',
    'hd',
    'clean',
    'action',
    'minViews',
    'hasMusic',
    'hasVoice',
    'hasDialogue',
    'materialType',
    'filterMode',
    'editMinScore',
    'durationRange',
    'film',
    'sort',
  ];

  const hasQuery = () => {
    const input = document.getElementById('searchInput');
    return Boolean((input?.value || '').trim());
  };

  const signature = () => filterIds.map((id) => {
    const element = document.getElementById(id);
    return `${id}=${element ? element.value : ''}`;
  }).join('&');

  const run = () => {
    if (!hasQuery()) {
      const status = document.getElementById('status');
      if (status) status.textContent = 'Сначала выполните поиск — после этого фильтры применяются автоматически.';
      return;
    }

    const nextSignature = signature();
    if (nextSignature === lastSignature) return;
    lastSignature = nextSignature;
    searchVideos();
  };

  filters.addEventListener('change', (event) => {
    if (!event.target.matches('select, input')) return;
    window.clearTimeout(debounceTimer);
    run();
  });

  filters.addEventListener('input', (event) => {
    if (!event.target.matches('input')) return;
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(run, 350);
  });

  const originalSearchVideos = window.searchVideos;
  if (typeof originalSearchVideos === 'function') {
    // The inline archive script is authoritative; this wrapper only records the latest filter signature.
    window.searchVideos = async (...args) => {
      lastSignature = signature();
      return originalSearchVideos(...args);
    };
  }

  lastSignature = signature();
})();
