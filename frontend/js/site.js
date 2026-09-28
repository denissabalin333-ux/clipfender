(()=>{
 const path=location.pathname.replace(/\/$/,'')||'/';
 const pageName=path==='/'?'home':path.slice(1).replace(/[^a-z0-9_-]/gi,'')||'home';
 document.body.dataset.page=pageName;

 // Accessibility: keyboard skip link without changing page markup contracts.
 if(!document.querySelector('.skip-link')){
   const main=document.querySelector('main');
   if(main){
     if(!main.id) main.id='main-content';
     const skip=document.createElement('a');
     skip.className='skip-link'; skip.href='#'+main.id; skip.textContent='Перейти к содержимому';
     document.body.prepend(skip);
   }
 }

 const navLinks=document.getElementById('navLinks');
 const menuBtn=document.querySelector('.mobile-menu-btn');
 const mobileBackdrop=document.querySelector('[data-mobile-backdrop]');
 document.querySelectorAll('.nav-links a[data-route]').forEach(a=>{if(a.dataset.route===path)a.classList.add('active')});

 const io='IntersectionObserver' in window?new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');io.unobserve(e.target)}}),{threshold:.08}):null;
 document.querySelectorAll('.reveal').forEach(e=>{if(io)io.observe(e);else e.classList.add('is-visible')});

 function setMenu(open){
   if(!navLinks) return;
   navLinks.classList.toggle('open',open);
   if(menuBtn){menuBtn.setAttribute('aria-expanded',String(open));menuBtn.setAttribute('aria-label',open?'Закрыть меню':'Открыть меню')}
   if(mobileBackdrop){mobileBackdrop.setAttribute('aria-hidden',String(!open));mobileBackdrop.classList.toggle('is-open',open)}
   document.body.classList.toggle('menu-open',open);
 }
 window.toggleMobileMenu=()=>setMenu(!navLinks?.classList.contains('open'));
 navLinks?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>setMenu(false)));
 mobileBackdrop?.addEventListener('click',()=>setMenu(false));
 window.addEventListener('resize',()=>{if(window.innerWidth>820 && navLinks?.classList.contains('open'))setMenu(false)}, {passive:true});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){setMenu(false);closeLore();}});

 window.scrollToTop=()=>window.scrollTo({top:0,behavior:'smooth'});
 window.openContact=()=>location.href='/contacts#form';
 window.goToArchive=()=>{const v=(document.getElementById('heroQuery')?.value||'').trim();location.href='/archive'+(v?'?q='+encodeURIComponent(v):'')};
 document.getElementById('heroQuery')?.addEventListener('keydown',e=>{if(e.key==='Enter')goToArchive()});

 window.showToast=(msg,type='info')=>{let t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';t.className='toast';t.setAttribute('role','status');t.setAttribute('aria-live','polite');document.body.appendChild(t)}t.dataset.type=type;t.textContent=msg;t.classList.add('show');clearTimeout(window.__toastTimer);window.__toastTimer=setTimeout(()=>t.classList.remove('show'),2800)};
 window.contactSubmit=(ev)=>{ev.preventDefault();const f=ev.target;const name=f.querySelector('[name=name]')?.value.trim();const email=f.querySelector('[name=email]')?.value.trim();localStorage.setItem('clipfinder_contact_draft',JSON.stringify({name,email,message:f.querySelector('textarea')?.value||''}));showToast('Заявка сохранена как тестовая. Данные не отправлены во внешний сервис.','success');const box=document.getElementById('contactMessage');if(box){box.hidden=false;box.textContent='✓ Тестовая заявка сохранена в браузере.'}return false};
 window.portfolioFilter=(kind)=>{document.querySelectorAll('[data-kind]').forEach(x=>{x.hidden=kind!=='all'&&x.dataset.kind!==kind});document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x.dataset.filter===kind))};
 window.faqToggle=(btn)=>{const item=btn.closest('.faq-item, .faq-item-rich');if(!item)return;const open=!item.classList.contains('open');item.classList.toggle('open',open);btn.setAttribute('aria-expanded',String(open));const answer=item.querySelector('.faq-answer');if(answer)answer.setAttribute('aria-hidden',String(!open))};
 window.loginDemo=(ev)=>{ev.preventDefault();localStorage.setItem('clipfinder_demo_user',document.querySelector('[name=login]')?.value||'Гость');showToast('Тестовый вход выполнен локально. Серверная авторизация пока не подключена.','success');return false};
 window.registerDemo=(ev)=>{ev.preventDefault();showToast('Тестовая регистрация выполнена локально. Пароль не отправлялся.','success');return false};
 window.characterSearch=(name)=>location.href='/archive?q='+encodeURIComponent(name);
 window.testHealth=async()=>{try{const r=await fetch('/health',{headers:{'Accept':'application/json'}});const d=await r.json();if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));showToast('Сервер работает: '+(d.status||'ok'),'success')}catch(e){showToast('Сервер недоступен','error')}};
 window.testQuota=async()=>{try{const r=await fetch('/api/quota',{headers:{'Accept':'application/json'}});const d=await r.json();if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));showToast(`Квота CLIPFINDER: ${d.used||0} / ${d.limit||0}. Осталось: ${d.remaining||0}`,'info')}catch(e){showToast('Не удалось получить статус квоты','error')}};

 window.showLore=(title,body,house)=>{const modal=document.getElementById('loreModal');if(!modal)return;document.getElementById('loreTitle').textContent=title;document.getElementById('loreBody').textContent=body;document.getElementById('loreHouse').textContent=house;modal.classList.add('active');document.querySelector('#loreModal .modal-close')?.focus()};
 window.closeLore=()=>document.getElementById('loreModal')?.classList.remove('active');
 window.closeLoreOutside=(e)=>{if(e.target.id==='loreModal')closeLore()};

 // Very slow hero parallax; disabled automatically for reduced motion.
 const hero=document.querySelector('.home-hero');
 if(hero && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
   let raf=0;
   hero.addEventListener('pointermove',e=>{
     const r=hero.getBoundingClientRect();
     const x=(e.clientX-r.left-r.width/2)/r.width*18;
     const y=(e.clientY-r.top-r.height/2)/r.height*18;
     cancelAnimationFrame(raf);raf=requestAnimationFrame(()=>{hero.style.setProperty('--mx',x+'px');hero.style.setProperty('--my',y+'px')});
   });
   hero.addEventListener('pointerleave',()=>{hero.style.setProperty('--mx','0px');hero.style.setProperty('--my','0px')});
 }
})();

// Legacy page-transition veil disabled in final reference build; final-reference.js owns the non-blocking transition.

// Default page-state accessibility values.
document.querySelectorAll('.faq-item button, .faq-item-rich button').forEach(btn=>{if(!btn.hasAttribute('aria-expanded'))btn.setAttribute('aria-expanded',String(btn.closest('.faq-item, .faq-item-rich')?.classList.contains('open')||false))});

// ============================================================
// CLIPFINDER V5.1 — interaction polish (additive)
// ============================================================
(function(){
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Scroll progress line.
  if(!document.getElementById('cf-scroll-progress')){
    const progress=document.createElement('div');
    progress.id='cf-scroll-progress';
    progress.setAttribute('aria-hidden','true');
    document.body.appendChild(progress);
    const update=()=>{
      const doc=document.documentElement;
      const max=doc.scrollHeight-doc.clientHeight;
      progress.style.width=(max>0?Math.min(100,(window.scrollY/max)*100):0)+'%';
    };
    window.addEventListener('scroll',update,{passive:true});
    window.addEventListener('resize',update,{passive:true});
    update();
  }

  // Click ripple for primary interactive controls.
  document.addEventListener('pointerdown',e=>{
    const target=e.target.closest('button,.btn,.nav-cta,.watch-button,.details-button,.favorite-button,.search-button,.show-all-button,.toolbar button,.controls button');
    if(!target || target.disabled || reduced) return;
    const r=target.getBoundingClientRect();
    const size=Math.max(r.width,r.height)*.55;
    const ripple=document.createElement('span');
    ripple.className='cf-ripple';
    ripple.style.width=size+'px'; ripple.style.height=size+'px';
    ripple.style.left=(e.clientX-r.left-size/2)+'px'; ripple.style.top=(e.clientY-r.top-size/2)+'px';
    target.appendChild(ripple);
    ripple.addEventListener('animationend',()=>ripple.remove(),{once:true});
  });

  // Pointer highlight on cards, deliberately subtle.
  if(!reduced){
    document.addEventListener('pointermove',e=>{
      const card=e.target.closest('.home-panel,.character-card-rich,.service-card-rich,.work-card-rich,.help-tool-card,.idea-card,.auth-card,.contact-chronicle,.contact-form-rich,.review,.faq-item-rich,.project-card-large,.featured-project-rich,.video-card');
      if(!card) return;
      const r=card.getBoundingClientRect();
      card.style.setProperty('--shine-x',((e.clientX-r.left)/r.width*100)+'%');
      card.style.setProperty('--shine-y',((e.clientY-r.top)/r.height*100)+'%');
    },{passive:true});
  }

  // Make hash links land cleanly below the fixed navigation.
  if(location.hash){
    requestAnimationFrame(()=>setTimeout(()=>{
      const el=document.querySelector(location.hash);
      if(el) el.scrollIntoView({behavior:reduced?'auto':'smooth',block:'start'});
    },120));
  }

  // Prevent accidental double-submit while keeping native form behaviour.
  document.querySelectorAll('form').forEach(form=>{
    form.addEventListener('submit',()=>{
      const submit=form.querySelector('button[type="submit"]');
      if(!submit || submit.dataset.busy==='1') return;
      submit.dataset.busy='1';
      const original=submit.textContent;
      submit.setAttribute('aria-busy','true');
      setTimeout(()=>{submit.dataset.busy='0';submit.removeAttribute('aria-busy');submit.textContent=original},900);
    });
  });
})();

// ============================================================
// CLIPFENDER V5.2 — live auth/contact actions (demo fallbacks kept)
// ============================================================
(function(){
  const getCookie = (name) => {
    const prefix = `${name}=`;
    const match = document.cookie.split('; ').find(item => item.startsWith(prefix));
    return match ? decodeURIComponent(match.slice(prefix.length)) : '';
  };

  const apiError = async (response) => {
    let detail = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) detail = Array.isArray(data.detail)
        ? data.detail.map(item => item.msg || item.message || String(item)).join('; ')
        : String(data.detail);
    } catch (_) {}
    const error = new Error(detail);
    error.status = response.status;
    return error;
  };

  window.ensureCsrfToken = async () => {
    const existing = getCookie('cf_csrf');
    if (existing) return existing;
    const response = await fetch('/api/auth/csrf', {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    });
    if (!response.ok) throw await apiError(response);
    const token = getCookie('cf_csrf');
    if (!token) throw new Error('Не удалось получить защитный токен формы');
    return token;
  };

  const setBusy = (button, busy, label) => {
    if (!button) return;
    if (busy) {
      button.dataset.liveBusy = '1';
      button.dataset.liveOriginal = button.textContent;
      button.setAttribute('aria-busy', 'true');
      button.disabled = true;
      if (label) button.textContent = label;
    } else {
      button.dataset.liveBusy = '0';
      button.removeAttribute('aria-busy');
      button.disabled = false;
      button.textContent = button.dataset.liveOriginal || button.textContent;
    }
  };

  const submitJson = async (url, payload) => {
    const csrf = await window.ensureCsrfToken();
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw await apiError(response);
    return response.json();
  };

  window.loginSubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget || event.target;
    const button = form.querySelector('button[type="submit"]');
    setBusy(button, true, 'ВХОД…');
    try {
      const data = await submitJson('/api/auth/login', {
        login: form.querySelector('[name=login]')?.value || '',
        password: form.querySelector('[name=password]')?.value || '',
        remember: Boolean(form.querySelector('[name=remember]')?.checked)
      });
      const name = data?.user?.name || 'редактор';
      window.showToast(`Добро пожаловать, ${name}.`, 'success');
      window.setTimeout(() => { location.href = '/archive'; }, 450);
    } catch (error) {
      window.showToast(error.message || 'Не удалось выполнить вход.', 'error');
    } finally {
      if (button?.dataset.liveBusy === '1') setBusy(button, false);
    }
    return false;
  };

  window.registerSubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget || event.target;
    const button = form.querySelector('button[type="submit"]');
    setBusy(button, true, 'СОЗДАЁМ АККАУНТ…');
    try {
      const data = await submitJson('/api/auth/register', {
        name: form.querySelector('[name=name]')?.value || '',
        email: form.querySelector('[name=email]')?.value || '',
        password: form.querySelector('[name=password]')?.value || ''
      });
      const name = data?.user?.name || 'редактор';
      window.showToast(`Аккаунт ${name} создан.`, 'success');
      window.setTimeout(() => { location.href = '/archive'; }, 450);
    } catch (error) {
      window.showToast(error.message || 'Не удалось создать аккаунт.', 'error');
    } finally {
      if (button?.dataset.liveBusy === '1') setBusy(button, false);
    }
    return false;
  };

  window.contactSubmitLive = async (event) => {
    event.preventDefault();
    const form = event.currentTarget || event.target;
    const button = form.querySelector('button[type="submit"]');
    const box = document.getElementById('contactMessage');
    setBusy(button, true, 'ОТПРАВЛЯЕМ…');
    try {
      const data = await submitJson('/api/contact', {
        name: form.querySelector('[name=name]')?.value || '',
        email: form.querySelector('[name=email]')?.value || '',
        message: form.querySelector('[name=message]')?.value || '',
        website: form.querySelector('[name=website]')?.value || ''
      });
      if (box) {
        box.hidden = false;
        box.textContent = `✓ ${data.message || 'Сообщение принято.'}`;
      }
      form.reset();
      window.showToast('Сообщение принято.', 'success');
    } catch (error) {
      if (box) {
        box.hidden = false;
        box.textContent = `× ${error.message || 'Не удалось отправить сообщение.'}`;
      }
      window.showToast(error.message || 'Не удалось отправить сообщение.', 'error');
    } finally {
      if (button?.dataset.liveBusy === '1') setBusy(button, false);
    }
    return false;
  };

  const liveAuthPage = document.querySelector('.auth-grid');
  const liveContactForm = document.querySelector('#form.contact-form-rich');
  if (liveAuthPage || liveContactForm) {
    window.ensureCsrfToken().catch(() => {});
  }
})();

// ============================================================
// CLIPFENDER V5.3 — Stage 5 visual/interaction layer
// Loaded after the existing site logic to preserve all legacy handlers.
// ============================================================
(() => {
  const bootStage5 = () => {
    if (document.documentElement.dataset.cf5Loaded) return;
    document.documentElement.dataset.cf5Loaded = '1';
    const script = document.createElement('script');
    script.src = '/static/js/stage5-atmosphere.js?v=80.0';
    script.defer = true;
    document.head.appendChild(script);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootStage5, { once: true });
  else bootStage5();
})();
