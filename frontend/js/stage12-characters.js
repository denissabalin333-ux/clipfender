(() => {
  'use strict';

  const root = document.getElementById('characterCatalog');
  if (!root) return;

  const cards = Array.from(root.querySelectorAll('.cf12-character-card'));
  const search = document.getElementById('cf12CharacterSearch');
  const house = document.getElementById('cf12HouseFilter');
  const profile = document.getElementById('cf12ProfileFilter');
  const reset = document.getElementById('cf12ResetFilters');
  const resetEmpty = document.getElementById('cf12ResetFiltersEmpty');
  const meta = document.getElementById('cf12CharacterMeta');
  const empty = document.getElementById('cf12CharactersEmpty');

  const favoriteKey = 'clipfender_character_favorites';

  const loadFavorites = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(favoriteKey) || '[]');
      return new Set(Array.isArray(parsed) ? parsed.map(String) : []);
    } catch (_) {
      return new Set();
    }
  };

  const saveFavorites = (set) => {
    localStorage.setItem(favoriteKey, JSON.stringify(Array.from(set)));
  };

  const normalize = (value) => String(value || '').trim().toLocaleLowerCase('ru-RU');

  const updateFavoriteButtons = () => {
    const favorites = loadFavorites();
    cards.forEach((card) => {
      const button = card.querySelector('[data-character-favorite]');
      if (!button) return;
      const active = favorites.has(String(button.dataset.characterFavorite || ''));
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
      button.textContent = active ? '★ СОХРАНЁН' : '☆ СОХРАНИТЬ';
      button.classList.toggle('is-active', active);
    });
  };

  const applyFilters = () => {
    const query = normalize(search?.value);
    const selectedHouse = normalize(house?.value);
    const selectedProfile = normalize(profile?.value);
    let visible = 0;

    cards.forEach((card) => {
      const name = normalize(card.dataset.characterName);
      const cardHouse = normalize(card.dataset.characterHouse);
      const profiles = normalize(card.dataset.characterProfiles).split(/\s+/).filter(Boolean);

      const matchesQuery = !query || name.includes(query);
      const matchesHouse = !selectedHouse || cardHouse === selectedHouse;
      const matchesProfile = !selectedProfile || profiles.includes(selectedProfile);
      const show = matchesQuery && matchesHouse && matchesProfile;

      card.hidden = !show;
      if (show) visible += 1;
    });

    if (meta) meta.textContent = `Показано: ${visible} из ${cards.length}`;
    if (empty) empty.hidden = visible !== 0;
  };

  const resetFilters = () => {
    if (search) search.value = '';
    if (house) house.value = '';
    if (profile) profile.value = '';
    applyFilters();
    search?.focus();
  };

  search?.addEventListener('input', applyFilters);
  house?.addEventListener('change', applyFilters);
  profile?.addEventListener('change', applyFilters);
  reset?.addEventListener('click', resetFilters);
  resetEmpty?.addEventListener('click', resetFilters);

  root.addEventListener('click', (event) => {
    const button = event.target.closest('[data-character-favorite]');
    if (!button) return;
    const slug = String(button.dataset.characterFavorite || '').trim();
    if (!slug) return;

    const favorites = loadFavorites();
    if (favorites.has(slug)) favorites.delete(slug);
    else favorites.add(slug);
    saveFavorites(favorites);
    updateFavoriteButtons();
  });

  updateFavoriteButtons();
  applyFilters();
})();
