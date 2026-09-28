(() => {
  const messages={
    ru:{
      'nav.home':'ГЛАВНАЯ','nav.searchCharacter':'НАЙТИ РОЛИК','nav.search':'ПОИСК','nav.characters':'ПЕРСОНАЖИ','nav.guides':'ГАЙДЫ','nav.ideas':'ИДЕИ','nav.help':'ПОМОЩЬ','nav.contacts':'КОНТАКТЫ','nav.library':'БИБЛИОТЕКА','nav.project':'О ПРОЕКТЕ','nav.login':'ВОЙТИ',
      'footer.tagline':'ЭПИЧЕСКИЕ МОМЕНТЫ<br>ДЛЯ ТВОИХ ИСТОРИЙ','footer.chronicles':'ХРОНИКИ CLIPFENDER','footer.privacy':'КОНФИДЕНЦИАЛЬНОСТЬ','footer.terms':'УСЛОВИЯ','footer.copyright':'ПРАВА','footer.service':'СЕРВИС ПОИСКА МАТЕРИАЛОВ ДЛЯ МОНТАЖА','footer.youtube':'ИСТОЧНИКИ: YOUTUBE',
      'report.open':'ПОЖАЛОВАТЬСЯ','report.reason':'Причина','report.details':'Комментарий','report.submit':'ОТПРАВИТЬ','common.cancel':'ОТМЕНА',
      'admin.kicker':'ОПЕРАЦИОННЫЙ ЗАЛ','admin.title':'АДМИН-ПАНЕЛЬ','admin.description':'Сводка сервиса, квота YouTube и очередь жалоб.','admin.users':'ПОЛЬЗОВАТЕЛИ','admin.videos':'ВИДЕО В БД','admin.searches':'ПОИСКОВ ЗА 24 Ч','admin.openReports':'ОТКРЫТЫХ ЖАЛОБ','admin.contacts':'НОВЫХ ОБРАЩЕНИЙ','admin.quota':'КВОТА','admin.topQueries':'ТОП ЗАПРОСОВ','admin.last7':'Последние 7 дней','admin.refresh':'ОБНОВИТЬ','admin.reports':'ЖАЛОБЫ','admin.reportQueue':'Очередь материалов',
      'language.toggle':'Переключить язык'
    },
    en:{
      'nav.home':'HOME','nav.searchCharacter':'FIND CLIP','nav.search':'SEARCH','nav.characters':'CHARACTERS','nav.guides':'GUIDES','nav.ideas':'IDEAS','nav.help':'HELP','nav.contacts':'CONTACTS','nav.library':'LIBRARY','nav.project':'ABOUT','nav.login':'SIGN IN',
      'footer.tagline':'EPIC MOMENTS<br>FOR YOUR STORIES','footer.chronicles':'CLIPFENDER CHRONICLES','footer.privacy':'PRIVACY','footer.terms':'TERMS','footer.copyright':'COPYRIGHT','footer.service':'VIDEO EDITING MATERIAL SEARCH SERVICE','footer.youtube':'SOURCES: YOUTUBE',
      'report.open':'REPORT','report.reason':'Reason','report.details':'Comment','report.submit':'SUBMIT','common.cancel':'CANCEL',
      'admin.kicker':'OPERATIONS ROOM','admin.title':'ADMIN PANEL','admin.description':'Service overview, YouTube quota and report queue.','admin.users':'USERS','admin.videos':'VIDEOS IN DB','admin.searches':'SEARCHES / 24H','admin.openReports':'OPEN REPORTS','admin.contacts':'NEW CONTACTS','admin.quota':'QUOTA','admin.topQueries':'TOP QUERIES','admin.last7':'Last 7 days','admin.refresh':'REFRESH','admin.reports':'REPORTS','admin.reportQueue':'Material queue',
      'language.toggle':'Switch language'
    }
  };
  const key=(document.documentElement.lang==='en'||localStorage.getItem('cf_locale')==='en')?'en':'ru';
  const apply=(locale)=>{
    const dict=messages[locale]||messages.ru;
    document.documentElement.lang=locale;
    document.querySelectorAll('[data-i18n]').forEach(el=>{const k=el.dataset.i18n;if(dict[k]!=null)el.innerHTML=dict[k]});
    document.querySelectorAll('[data-i18n-aria]').forEach(el=>{const k=el.dataset.i18nAria||el.getAttribute('data-i18n-aria');if(dict[k]!=null)el.setAttribute('aria-label',dict[k])});
    const label=document.querySelector('[data-cf-language-label]');if(label)label.textContent=locale==='ru'?'EN':'RU';
    localStorage.setItem('cf_locale',locale);
  };
  document.addEventListener('click',e=>{const btn=e.target.closest('[data-cf-language-toggle]');if(!btn)return;apply((document.documentElement.lang==='en')?'ru':'en')});
  const boot=()=>apply(key);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
