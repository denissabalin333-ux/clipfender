# CLIPFENDER — ЭТАП 3: таблица интерактивных элементов

Публичные страницы и общий shell. `component-kit.html` не включён: это внутренний showcase, не публичный маршрут.

| Страница | Элемент | Ожидаемое действие | Результат |
|---|---|---|---|
| header/footer | Логотип / ГЛАВНАЯ | Перейти на главную | GET / |
| header/footer | НАЙТИ РОЛИК | Открыть поиск персонажа | GET /character-search |
| header/footer | ПЕРСОНАЖИ | Открыть каталог персонажей | GET /characters |
| header/footer | ИДЕИ ДЛЯ ЭДИТОВ | Открыть монтажные идеи | GET /edit-ideas |
| header/footer | ГАЙДЫ | Открыть гайды | GET /guides |
| header/footer | ПОМОЩЬ | Открыть помощь | GET /help |
| header/footer | О ПРОЕКТЕ | Открыть проект | GET /project |
| header/footer | ВОЙТИ | Открыть авторизацию | GET /login |
| header/footer | ПОИСК / КОНТАКТЫ / ИДЕИ… | Переход по footer-разделу | GET соответствующей страницы |
| frontend/index.html | Форма #homeStage3Search | Передать запрос в архив | GET /archive?q=... |
| frontend/index.html | ОТКРЫТЬ АРХИВ | Открыть архив | GET /archive |
| frontend/index.html | СМОТРЕТЬ ГЕРОЕВ | Открыть персонажей | GET /characters |
| frontend/index.html | ОТКРЫТЬ ИДЕИ | Открыть идеи | GET /edit-ideas |
| frontend/archive.html | cf4SearchMirror | Фокусировать/открыть поиск | Пользователь возвращается к поисковому полю |
| frontend/archive.html | cf4FilterOpen | Открыть фильтры | Показывается filter modal/panel |
| frontend/archive.html | searchButton | Выполнить поиск | GET /api/search с текущими параметрами |
| frontend/archive.html | Сбросить | resetFilters() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Обновить | refreshSearch() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Лучшие для эдита | setPreset('best') | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Cinematic | setPreset('cinematic') | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Raw footage | setPreset('raw') | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | С музыкой | setPreset('audio') | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Избранное | showFavorites() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Поделиться | shareSearch() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Справка | showHelp() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Наверх | scrollToTop() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Назад | previousPage() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Вперёд | nextPage() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Показать все | showAllVideos() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | Загрузить ещё 50 | loadMoreVideos() | Состояние архива изменяется без потери текущего поиска |
| frontend/archive.html | video-card / ОТКРЫТЬ | Открыть карточку/просмотр | Открывается detail modal или /video?id=... |
| frontend/archive.html | favorite-button | Переключить избранное | Материал добавляется/убирается из локального избранного |
| frontend/archive.html | watch-button | Открыть YouTube | Официальная ссылка YouTube |
| frontend/archive.html | modal-close / favorites / help | Закрыть модальное окно | Modal скрывается |
| frontend/pages/404.html | ВЕРНУТЬСЯ В CLIPFENDER | Вернуться на главную | GET / |
| frontend/pages/about.html | НАПИСАТЬ МНЕ | Открыть контакты | GET /contacts |
| frontend/pages/about.html | ПОСМОТРЕТЬ РАБОТЫ | Открыть портфолио | GET /portfolio |
| frontend/pages/character-search.html | Форма #characterSearchForm | Найти персонажа | Профиль или fallback в /archive?q=... |
| frontend/pages/character-search.html | 6 популярных карточек | Открыть сцену персонажа | GET /archive?q=... |
| frontend/pages/character-search.html | ИСТОРИЯ (динамическая) | Открыть lore modal | Открывается модалка истории персонажа |
| frontend/pages/characters.html | Кнопка ПОИСК | Фокус на #cfCharacterSearch | Search input получает focus |
| frontend/pages/characters.html | 6 кнопок ☆ В ИЗБРАННОЕ | Переключить избранного персонажа | localStorage + визуальное состояние кнопки |
| frontend/pages/characters.html | 6 кнопок НАЙТИ РОЛИКИ | Открыть архив персонажа | GET /archive?q=... |
| frontend/pages/contacts.html | Форма #form | Отправить контакт | POST /api/contact + SQLite + optional SMTP/Telegram |
| frontend/pages/contacts.html | honeypot website | Антибот-защита | Заполненный honeypot не сохраняется |
| frontend/pages/contacts.html | contactSubmit | Старый demo fallback | Остаётся в site.js |
| frontend/pages/edit-ideas.html | Поиск #cfIdeaSearchV7 + Enter | Фильтровать идеи/передать запрос | Фильтр или GET /archive?q=... cinematic edit |
| frontend/pages/edit-ideas.html | Категории идеи | Изменить фильтр категории | Показываются совпадающие карточки |
| frontend/pages/edit-ideas.html | Популярные запросы | Заполнить поиск | Input получает значение |
| frontend/pages/edit-ideas.html | ПОДРОБНЕЕ | Открыть идею | Открывается detail modal |
| frontend/pages/edit-ideas.html | СЦЕНЫ | Найти реальные сцены | GET /archive?q=... |
| frontend/pages/edit-ideas.html | СОХРАНИТЬ | Переключить сохранение идеи | localStorage + визуальное состояние |
| frontend/pages/faq.html | 6 FAQ-кнопок | Открыть/закрыть ответ | Accordion + aria-expanded |
| frontend/pages/faq.html | ОТКРЫТЬ ГАЙД | Открыть помощь | GET /help |
| frontend/pages/faq.html | НАПИСАТЬ | Открыть контакты | GET /contacts |
| frontend/pages/guides.html | Форма #cfGuideSearchV7 | Передать запрос в архив | GET /archive?q=... |
| frontend/pages/guides.html | ОТКРЫТЬ FAQ | Открыть FAQ | GET /faq |
| frontend/pages/help.html | ПРОВЕРИТЬ СЕРВЕР | Проверить /health | Toast с результатом health-check |
| frontend/pages/help.html | ПРОВЕРИТЬ КВОТУ | Проверить /api/quota | Toast со статусом квоты |
| frontend/pages/help.html | 6 карточек помощи | Открыть соответствующий раздел | GET целевой страницы |
| frontend/pages/login.html | Форма ВОЙТИ | Серверный вход | POST /api/auth/login + httpOnly session cookie |
| frontend/pages/login.html | Запомнить меня на 30 дней | Выбрать срок сессии | 8 часов без флажка / 30 дней с флажком |
| frontend/pages/login.html | Форма РЕГИСТРАЦИЯ | Создать аккаунт | POST /api/auth/register + Argon2 + session cookie |
| frontend/pages/login.html | loginDemo/registerDemo | Сохранённый demo fallback | Остаются в JS и не удалены |
| frontend/pages/portfolio.html | 6 фильтров портфолио | Фильтровать карточки | Скрываются/показываются data-kind |
| frontend/pages/portfolio.html | СМОТРЕТЬ ПРОЕКТ | Открыть контакты | GET /contacts |
| frontend/pages/project.html | НАЧАТЬ ПОИСК | Открыть character search | GET /character-search |
| frontend/pages/project.html | ОТКРЫТЬ ИДЕИ | Открыть edit ideas | GET /edit-ideas |
| frontend/pages/services.html | ОБСУДИТЬ ПРОЕКТ / ЗАКАЗАТЬ | Открыть форму контактов | GET /contacts#form |
| frontend/pages/video.html | НАЗАД К АРХИВУ | Вернуться в архив | GET /archive |
| frontend/pages/video.html | ОТКРЫТЬ АРХИВ / youtubeLink | Перейти к исходному материалу | YouTube URL из /api/video/{id} |

## Backend actions

| Endpoint | Назначение | Защита | Результат |
|---|---|---|---|
| `/api/auth/csrf` | Получение double-submit CSRF cookie | SameSite cookie | `200` |
| `/api/auth/register` | Регистрация + автоматический login | CSRF + rate-limit + Argon2 | `200/409/422/429` |
| `/api/auth/login` | Вход | CSRF + rate-limit + Argon2 + httpOnly session cookie | `200/401/422/429` |
| `/api/auth/logout` | Удаление сессии | CSRF | `200` |
| `/api/auth/me` | Текущее состояние сессии | httpOnly cookie | `200` |
| `/api/contact` | Сохранение сообщения + уведомление | CSRF + honeypot + rate-limit | `200/422/429` |

## Demo fallbacks preserved

`loginDemo`, `registerDemo`, `contactSubmit` не удалены и остаются резервным локальным режимом. Публичные формы теперь используют серверные `loginSubmit`, `registerSubmit`, `contactSubmitLive`.
