(() => {
  const panel=document.querySelector('[data-cf-report-panel]');
  const form=document.querySelector('[data-cf-report-form]');
  if(!panel||!form)return;
  const open=document.querySelector('[data-cf-report-open]');
  const cancel=document.querySelector('[data-cf-report-cancel]');
  const status=document.querySelector('[data-cf-report-status]');
  const videoId=new URLSearchParams(location.search).get('id')||'';
  fetch('/api/auth/me',{headers:{Accept:'application/json'}}).then(r=>r.json()).then(d=>{panel.hidden=!d.authenticated}).catch(()=>{panel.hidden=true});
  open?.addEventListener('click',()=>{form.hidden=false;open.hidden=true});
  cancel?.addEventListener('click',()=>{form.hidden=true;open.hidden=false});
  const getCsrf=()=>document.cookie.split('; ').find(v=>v.startsWith('cf_csrf='))?.slice(8)||'';
  form.addEventListener('submit',async(e)=>{
    e.preventDefault();
    status.textContent='';
    try{
      await fetch('/api/auth/csrf',{headers:{Accept:'application/json'}});
      const body={video_id:videoId,reason:form.reason.value,details:form.details.value};
      const r=await fetch('/api/reports',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':getCsrf(),Accept:'application/json'},body:JSON.stringify(body)});
      const d=await r.json();
      if(!r.ok)throw new Error(d.detail||'Не удалось отправить жалобу');
      status.textContent='Жалоба отправлена.';
      form.reset();
    }catch(error){status.textContent=error.message||'Не удалось отправить жалобу'}
  });
})();
