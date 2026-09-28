(() => {
  const dashboard = document.querySelectorAll('[data-admin-dashboard]');
  if (!dashboard.length) return;
  const status = document.querySelector('[data-admin-status]');
  const table = document.querySelector('[data-admin-reports]');
  const reportStatus = document.querySelector('[data-admin-report-status]');
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const csrf = async () => {
    const r = await fetch('/api/auth/csrf', {headers:{Accept:'application/json'}});
    if (!r.ok) throw new Error('CSRF');
    const d = await r.json();
    return d;
  };
  const getCsrf = () => document.cookie.split('; ').find(v => v.startsWith('cf_csrf='))?.slice(8) || '';
  async function loadSummary(){
    const r = await fetch('/api/admin/summary',{headers:{Accept:'application/json'}});
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || 'Admin');
    document.querySelector('[data-stat="users"]').textContent=d.users;
    document.querySelector('[data-stat="videos"]').textContent=d.videos;
    document.querySelector('[data-stat="searches_24h"]').textContent=d.searches_24h;
    document.querySelector('[data-stat="open_reports"]').textContent=d.open_reports;
    document.querySelector('[data-stat="new_contacts"]').textContent=d.new_contacts;
    document.querySelector('[data-stat="quota"]').textContent=`${d.quota.used} / ${d.quota.limit}`;
    document.querySelector('[data-stat="quotaRemaining"]').textContent=`Осталось: ${d.quota.remaining}`;
    const list=document.querySelector('[data-admin-top-queries]');
    list.innerHTML=d.top_queries.length?d.top_queries.map(item=>`<li><strong>${esc(item.query)}</strong> <span>×${item.count}</span></li>`).join(''):'<li>Пока нет истории поисков.</li>';
  }
  async function loadReports(){
    const r=await fetch(`/api/admin/reports?status=${encodeURIComponent(reportStatus.value)}`,{headers:{Accept:'application/json'}});
    const d=await r.json();
    if(!r.ok) throw new Error(d.detail||'Reports');
    table.innerHTML=d.items.length?d.items.map(item=>`<tr><td>#${item.id}</td><td><a href="/video?id=${encodeURIComponent(item.video_id)}" target="_blank" rel="noopener">${esc(item.video_id)}</a></td><td>${esc(item.reason)}</td><td>${esc(item.details||'—')}</td><td>${esc(item.reporter?.name||'—')}<br><small>${esc(item.reporter?.email||'')}</small></td><td>${esc(item.created_at||'—')}</td><td><span class="admin-report-status ${item.status}">${esc(item.status)}</span></td><td>${item.status==='open'?`<button class="btn btn-secondary" type="button" data-resolve-report="${item.id}">Закрыть</button>`:`<button class="btn btn-secondary" type="button" data-reopen-report="${item.id}">Открыть</button>`}</td></tr>`).join(''):'<tr><td colspan="8">Нет жалоб.</td></tr>';
  }
  async function updateReport(id,statusValue){
    await csrf();
    const r=await fetch(`/api/admin/reports/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json','X-CSRF-Token':getCsrf(),Accept:'application/json'},body:JSON.stringify({status:statusValue})});
    const d=await r.json();
    if(!r.ok) throw new Error(d.detail||'Report update');
  }
  async function boot(){
    try{
      await csrf();
      await loadSummary();
      await loadReports();
      dashboard.forEach(el=>{el.hidden=false});
      status.textContent='';
    }catch(error){
      status.dataset.state='error';
      status.textContent=error.message||'Доступ запрещён.';
    }
  }
  document.querySelector('[data-admin-refresh]')?.addEventListener('click',()=>Promise.all([loadSummary(),loadReports()]).catch(e=>{status.dataset.state='error';status.textContent=e.message}));
  reportStatus?.addEventListener('change',()=>loadReports().catch(e=>{status.dataset.state='error';status.textContent=e.message}));
  table?.addEventListener('click',async(e)=>{
    const resolve=e.target.closest('[data-resolve-report]');
    const reopen=e.target.closest('[data-reopen-report]');
    const target=resolve||reopen;
    if(!target)return;
    try{await updateReport(target.dataset.resolveReport||target.dataset.reopenReport,resolve?'resolved':'open');await loadSummary();await loadReports()}catch(error){status.dataset.state='error';status.textContent=error.message||'Ошибка обновления'}
  });
  boot();
})();
