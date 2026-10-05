(() => {
  'use strict';
  const api = async (path, options = {}) => {
    const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { Accept: 'application/json', ...(options.headers || {}) } });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try { const data = await response.json(); if (data?.detail) message = Array.isArray(data.detail) ? data.detail.map(x => x.msg || '').join('; ') : String(data.detail); } catch (_) {}
      const error = new Error(message); error.status = response.status; throw error;
    }
    return response.json();
  };
  const csrf = () => window.ensureCsrfToken ? window.ensureCsrfToken() : fetch('/api/auth/csrf', {credentials:'same-origin'}).then(async r => { if(!r.ok) throw new Error('Не удалось получить CSRF'); return (document.cookie.split('; ').find(x=>x.startsWith('cf_csrf='))?.split('=')[1] || ''); });
  const post = async (path, payload) => { const token = await csrf(); return api(path, {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':token}, body:JSON.stringify(payload)}); };
  const del = async (path) => { const token = await csrf(); return api(path, {method:'DELETE', headers:{'X-CSRF-Token':token}}); };

  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
  const getCookie = name => document.cookie.split('; ').find(x=>x.startsWith(name+'='))?.slice(name.length+1) || '';

  async function currentUser() { const data = await api('/api/auth/me'); return data?.authenticated ? data.user : null; }

  // ---------------- archive: server favourites + URL state ----------------
  if (document.getElementById('searchInput') && typeof window.searchVideos === 'function') {
    const originalSearch = window.searchVideos;
    const originalNext = window.nextPage;
    const originalPrevious = window.previousPage;
    const originalLoadMore = window.loadMoreVideos;
    const originalToggleFavorite = window.toggleFavorite;
    let restoringUrl = false;

    const filterIds = ['minViews','shorts','hd','clean','action','hasMusic','hasVoice','hasDialogue','materialType','filterMode','editMinScore','durationRange','sort'];
    const stateFromForm = () => {
      const params = new URLSearchParams();
      const q = document.getElementById('searchInput')?.value.trim() || '';
      if (q) params.set('q', q);
      for (const id of filterIds) { const el = document.getElementById(id); if (!el) continue; const value = el.value; if (value && value !== '0') params.set(id, value); }
      params.set('page', String(typeof currentPage === 'number' ? currentPage : 1));
      return params;
    };
    const replaceArchiveUrl = (push = false) => {
      const url = new URL(location.href); const params = stateFromForm();
      url.search = params.toString();
      history[push ? 'pushState' : 'replaceState']({cf6:true}, '', url);
    };
    const applyUrl = () => {
      const params = new URLSearchParams(location.search);
      const q = params.get('q') || '';
      if (q) document.getElementById('searchInput').value = q;
      for (const id of filterIds) { const el = document.getElementById(id); if (!el) continue; const value = params.get(id); if (value !== null) el.value = value; }
      return {q, page: Math.max(1, Number(params.get('page') || 1))};
    };

    window.searchVideos = async function(...args) {
      const result = await originalSearch.apply(this, args);
      replaceArchiveUrl(!restoringUrl && Boolean(document.getElementById('searchInput')?.value.trim()));
      try {
        const user = await currentUser();
        if (user && document.getElementById('searchInput')?.value.trim() && document.getElementById('error')?.style.display !== 'block') {
          await post('/api/library/history', {query: document.getElementById('searchInput').value.trim(), params: Object.fromEntries(new URLSearchParams(location.search).entries())});
        }
      } catch (_) {}
      return result;
    };

    window.nextPage = async function(...args) { const result = await originalNext.apply(this, args); if (!restoringUrl) replaceArchiveUrl(true); return result; };
    window.previousPage = async function(...args) { const result = await originalPrevious.apply(this, args); if (!restoringUrl) replaceArchiveUrl(true); return result; };
    window.loadMoreVideos = async function(...args) { const result = await originalLoadMore.apply(this, args); if (!restoringUrl) replaceArchiveUrl(true); return result; };

    window.toggleFavorite = async function(id) {
      const key = String(id);

      try {
        const user = await currentUser();

        if (!user) {
          window.showToast?.('Войди в аккаунт, чтобы сохранять материалы в библиотеку.', 'error');
          window.setTimeout(() => {
            window.location.href = '/login';
          }, 250);
          return;
        }

        const video = typeof videoStore !== 'undefined' ? videoStore.get(key) : null;
        const active = typeof isFavorite === 'function' && isFavorite(key);

        // Server is the source of truth. Do not mutate the local state until
        // the database operation succeeds.
        if (active) {
          await del('/api/library/favorites/' + encodeURIComponent(key));
        } else {
          await post('/api/library/favorites', {
            video_id: key,
            video: video || {id: key},
          });
        }

        // Refresh the local cache from the server after a successful mutation.
        await syncServerFavorites();

        if (typeof renderFavoriteState === 'function') {
          renderFavoriteState(key);
        }

        window.showToast?.(
          active ? 'Материал убран из избранного.' : 'Материал сохранён в библиотеку.',
          'success'
        );
      } catch (error) {
        window.showToast?.(
          error?.message || 'Не удалось изменить избранное.',
          'error'
        );

        // Recover the visible state from the server.
        try {
          await syncServerFavorites();
          if (typeof renderFavoriteState === 'function') {
            renderFavoriteState(key);
          }
        } catch (_) {
          // Keep the original error visible.
        }
      }
    };

    async function syncServerFavorites() {
      const user = await currentUser(); if (!user) return false;
      const data = await api('/api/library/favorites'); const map = {};
      for (const item of data.items || []) map[String(item.video_id)] = item.video || {id:item.video_id};
      localStorage.setItem('clipfender_favorites', JSON.stringify(map));
      if (typeof renderFavoriteState === 'function') renderFavoriteState('');
      return true;
    }
    window.syncServerFavorites = syncServerFavorites;

    window.saveCurrentSearch = async function() {
      try {
        const user = await currentUser();
        if (!user) { window.showToast?.('Войди в ClipFender, чтобы сохранять фильтры.', 'error'); location.href = '/login'; return; }
        const current = stateFromForm();
        const name = prompt('Название сохранённого поиска:', current.get('q') || 'Новый набор фильтров');
        if (!name) return;
        const filters = {}; for (const [key, value] of current.entries()) if (key !== 'q' && key !== 'page') filters[key] = value;
        await post('/api/library/filters', {name, query: current.get('q') || '', filters});
        window.showToast?.('Поиск сохранён в библиотеке.', 'success');
      } catch (error) { window.showToast?.(error.message || 'Не удалось сохранить фильтры.', 'error'); }
    };

    window.openLibrary = () => { location.href = '/library'; };

    const restorePage = async targetPage => {
      const target = Math.max(1, Math.min(20, Number(targetPage || 1)));
      while (typeof currentPage === 'number' && currentPage < target && typeof originalNext === 'function') {
        const before = currentPage;
        await originalNext();
        if (currentPage <= before) break;
      }
    };
    const restoreArchiveState = async state => {
      if (!state.q) return;
      restoringUrl = true;
      try {
        await window.searchVideos();
        await restorePage(state.page);
        replaceArchiveUrl(false);
      } finally {
        restoringUrl = false;
      }
    };
    const restore = applyUrl();
    if (restore.q && [...new URLSearchParams(location.search).keys()].some(k => k !== 'q')) queueMicrotask(() => restoreArchiveState(restore));
    addEventListener('popstate', () => { const state = applyUrl(); if (!state.q) return; restoreArchiveState(state); });

    currentUser().then(user => {
      if (user) syncServerFavorites().catch(() => {});
    }).catch(() => {});

    window.addEventListener('clipfender:auth-changed', event => {
      if (event.detail?.authenticated) {
        syncServerFavorites().catch(() => {});
      }
    });

    document.addEventListener('DOMContentLoaded', () => {
      const toolbar = document.querySelector('.toolbar');
      if (toolbar && !document.getElementById('saveSearchButton')) {
        const save = document.createElement('button'); save.id='saveSearchButton'; save.type='button'; save.textContent='▤ Сохранить поиск'; save.onclick=window.saveCurrentSearch;
        const library = document.createElement('button'); library.type='button'; library.textContent='✦ Моя библиотека'; library.onclick=window.openLibrary;
        toolbar.append(save, library);
      }
    });
  }

  // ---------------- library page ----------------
  const libraryPage = document.getElementById('libraryContent');
  if (libraryPage) {
    const gate = document.getElementById('libraryAuthGate');
    let collections = [];
    let favorites = [];
    const reloadCollections = async () => { const data = await api('/api/library/collections'); collections = data.items || []; return collections; };
    const renderCollections = () => {
      const host = document.getElementById('libraryCollections');
      if (!collections.length) { host.innerHTML='<div class="cf-library-empty">Создай первую коллекцию для конкретного эдита.</div>'; return; }
      host.innerHTML = collections.map(c => `<div class="cf-library-collection"><div class="cf-library-collection__row"><div><h4>${esc(c.name)}</h4><p>${esc(c.description || 'Без описания')}</p></div><span class="cf-library-collection__meta">${c.item_count} кадр.</span></div><div class="cf-library-card__actions"><button type="button" data-open-collection="${c.id}">ОТКРЫТЬ</button><button type="button" data-export-collection="${c.id}" data-export-format="csv">CSV</button><button type="button" data-export-collection="${c.id}" data-export-format="json">JSON</button><button type="button" data-export-collection="${c.id}" data-export-format="markdown">MD</button><button type="button" data-delete-collection="${c.id}">УДАЛИТЬ</button></div></div>`).join('');
      host.querySelectorAll('[data-open-collection]').forEach(b=>b.addEventListener('click',()=>openCollection(Number(b.dataset.openCollection))));
      host.querySelectorAll('[data-export-collection]').forEach(b=>b.addEventListener('click',()=>window.exportLibrary(b.dataset.exportFormat, Number(b.dataset.exportCollection))));
      host.querySelectorAll('[data-delete-collection]').forEach(b=>b.addEventListener('click',async()=>{if(!confirm('Удалить коллекцию?'))return; await del('/api/library/collections/'+b.dataset.deleteCollection); await reloadCollections(); renderCollections(); renderFavorites();}));
    };
    const collectionOptions = () => `<option value="">В коллекцию…</option>${collections.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('')}`;
    const renderFavorites = () => {
      const host=document.getElementById('libraryFavorites'); document.getElementById('favoriteCount').textContent=favorites.length;
      if (!favorites.length) { host.innerHTML='<div class="cf-library-empty">Избранных материалов пока нет. На странице архива нажимай ★ у нужного кадра.</div>'; return; }
      host.innerHTML=favorites.map(item=>{const v=item.video||{}; const id=esc(item.video_id||v.id); const title=esc(v.title||'Без названия'); const thumb=esc(v.thumbnail||`https://i.ytimg.com/vi/${encodeURIComponent(item.video_id)}/hqdefault.jpg`); const url=esc(v.url||`https://www.youtube.com/watch?v=${encodeURIComponent(item.video_id)}`); return `<article class="cf-library-card"><img src="${thumb}" alt="${title}" loading="lazy"><div><h4>${title}</h4><p>${esc(v.channel||'')} · Edit Score ${esc(v.edit_score ?? v.score ?? 0)} · ${esc(v.duration||'—')}</p><div class="cf-library-card__actions"><a href="${url}" target="_blank" rel="noopener noreferrer">ОТКРЫТЬ НА YOUTUBE</a><select class="cf-library-collection__select" data-collection-select="${id}">${collectionOptions()}</select><button type="button" data-add-collection="${id}">ДОБАВИТЬ</button><button type="button" data-remove-favorite="${id}">УБРАТЬ</button></div></div></article>`;}).join('');
      host.querySelectorAll('[data-add-collection]').forEach(b=>b.addEventListener('click',async()=>{const id=b.dataset.addCollection; const select=host.querySelector(`[data-collection-select="${CSS.escape(id)}"]`); const collectionId=select?.value; if(!collectionId){window.showToast?.('Выбери коллекцию.','error');return;} const favorite=favorites.find(x=>String(x.video_id)===id); await post('/api/library/collections/'+collectionId+'/items',{video_id:id,video:favorite?.video||{id}}); await reloadCollections(); renderCollections(); window.showToast?.('Кадр добавлен в коллекцию.','success');}));
      host.querySelectorAll('[data-remove-favorite]').forEach(b=>b.addEventListener('click',async()=>{await del('/api/library/favorites/'+encodeURIComponent(b.dataset.removeFavorite)); await loadAll(); window.showToast?.('Кадр убран из избранного.','success');}));
    };
    const renderHistory = async () => { const host=document.getElementById('libraryHistory'); const data=await api('/api/library/history'); const items=data.items||[]; host.innerHTML=items.length?items.map(x=>{const params=new URLSearchParams(x.params||{}); const q=x.query; if(q)params.set('q',q); return `<div class="cf-library-history__item"><a href="/archive?${params.toString()}">${esc(q)}</a><small>${esc(x.created_at||'')}</small></div>`}).join(''):'<div class="cf-library-empty">История поиска появится после первого запроса.</div>'; };
    const renderSavedFilters = async () => { const host=document.getElementById('librarySavedFilters'); const data=await api('/api/library/filters'); const items=data.items||[]; host.innerHTML=items.length?items.map(x=>{const params=new URLSearchParams(x.filters||{}); if(x.query)params.set('q',x.query); return `<div class="cf-library-history__item"><a href="/archive?${params.toString()}">${esc(x.name)}</a><small>${esc(x.query||'Без запроса')} · <button type="button" data-delete-filter="${x.id}" style="border:0;background:none;color:#9a7b50;cursor:pointer">Удалить</button></small></div>`}).join(''):'<div class="cf-library-empty">Сохранённых фильтров пока нет.</div>'; host.querySelectorAll('[data-delete-filter]').forEach(b=>b.addEventListener('click',async()=>{await del('/api/library/filters/'+b.dataset.deleteFilter); renderSavedFilters();})); };
    async function openCollection(id){ const data=await api('/api/library/collections/'+id); favorites=data.items.map(x=>({video_id:x.video_id,video:x.video})); document.getElementById('favoriteCount').textContent=favorites.length; renderFavorites(); }
    async function loadAll(){ const [favData]=await Promise.all([api('/api/library/favorites'),reloadCollections()]); favorites=favData.items||[]; renderCollections(); renderFavorites(); await renderHistory(); await renderSavedFilters(); }
    window.exportLibrary = async format => { try { const response=await fetch('/api/library/export?format='+encodeURIComponent(format),{credentials:'same-origin'}); if(!response.ok){throw new Error('HTTP '+response.status)} const blob=await response.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a');a.href=url;a.download='clipfender-favorites.'+(format==='markdown'?'md':format);a.click();URL.revokeObjectURL(url);} catch(e){window.showToast?.('Не удалось подготовить экспорт.','error');} };
    window.clearSearchHistory = async () => { if(!confirm('Очистить историю поисков?')) return; try{await del('/api/library/history');await renderHistory();}catch(e){window.showToast?.(e.message,'error');} };
    document.getElementById('collectionForm')?.addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget;try{await post('/api/library/collections',{name:form.name.value,description:form.description.value});form.reset();await reloadCollections();renderCollections();renderFavorites();window.showToast?.('Коллекция создана.','success');}catch(err){window.showToast?.(err.message,'error');}});
    currentUser().then(user=>{if(!user){gate.hidden=false;libraryPage.hidden=true;return;} gate.hidden=true;libraryPage.hidden=false;loadAll().catch(err=>window.showToast?.(err.message,'error'));}).catch(()=>{gate.hidden=false;libraryPage.hidden=true;});
  }
})();
