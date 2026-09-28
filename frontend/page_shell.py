"""Shared HTML shell and public metadata for ClipFender pages."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urljoin

from fastapi import Request
from fastapi.templating import Jinja2Templates

FRONTEND_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(FRONTEND_DIR))

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

SEO_PAGES = {
    "index.html": {
        "title": "CLIPFENDER — поиск сцен для эдитов",
        "description": "ClipFender помогает находить YouTube-материалы и сцены для эдитов по персонажам, настроению и монтажным фильтрам.",
        "path": "/",
    },
    "archive.html": {
        "title": "Архив материалов — CLIPFENDER",
        "description": "Поиск сцен и YouTube-материалов для эдитов: персонаж, качество, сцена, Edit Score и другие фильтры.",
        "path": "/archive",
    },
    "pages/search.html": {
        "title": "Поиск и идея для эдита — CLIPFENDER",
        "description": "Полноэкранный поиск ClipFender: обычный поиск и сценарий эдита на основе реальных материалов из локальной базы.",
        "path": "/search",
    },
    "pages/character-search.html": {
        "title": "Поиск роликов персонажа — CLIPFENDER",
        "description": "Найдите сцены конкретного персонажа для монтажа и быстро перейдите к материалам в архиве ClipFender.",
        "path": "/character-search",
    },
    "pages/characters.html": {
        "title": "Персонажи — CLIPFENDER",
        "description": "Каталог персонажей и быстрый переход к материалам, сценам и монтажным подборкам ClipFender.",
        "path": "/characters",
    },
    "pages/guides.html": {
        "title": "Гайды по монтажу — CLIPFENDER",
        "description": "Практические гайды ClipFender по поиску материала, сценам, фильтрам и подготовке кадров для эдитов.",
        "path": "/guides",
    },
    "pages/edit-ideas.html": {
        "title": "Идеи для эдитов — CLIPFENDER",
        "description": "Идеи для эдитов, настроение, персонаж и монтажные направления внутри ClipFender.",
        "path": "/edit-ideas",
    },
    "pages/video.html": {
        "title": "Просмотр материала — CLIPFENDER",
        "description": "Просмотр выбранного YouTube-материала через официальный встроенный плеер и переход к источнику.",
        "path": "/video",
    },
    "pages/portfolio.html": {
        "title": "Портфолио — CLIPFENDER",
        "description": "Примеры монтажных направлений и визуальная подборка ClipFender.",
        "path": "/portfolio",
    },
    "pages/services.html": {
        "title": "Услуги — CLIPFENDER",
        "description": "Информация об услугах и возможностях ClipFender для монтажных задач.",
        "path": "/services",
    },
    "pages/about.html": {
        "title": "О проекте — CLIPFENDER",
        "description": "О проекте ClipFender, его назначении и принципах работы с материалами для монтажа.",
        "path": "/about",
    },
    "pages/contacts.html": {
        "title": "Контакты — CLIPFENDER",
        "description": "Связаться с командой ClipFender, сообщить о проблеме или отправить обращение.",
        "path": "/contacts",
    },
    "pages/help.html": {
        "title": "Помощь — CLIPFENDER",
        "description": "Ответы на частые вопросы по поиску, фильтрам, аккаунту и библиотеке ClipFender.",
        "path": "/help",
    },
    "pages/faq.html": {
        "title": "Частые вопросы — CLIPFENDER",
        "description": "Частые вопросы о поиске роликов, квоте YouTube, аккаунте и сохранённых материалах.",
        "path": "/faq",
    },
    "pages/project.html": {
        "title": "О ClipFender — CLIPFENDER",
        "description": "Документация и описание проекта ClipFender — сервиса поиска материалов для видеомонтажа.",
        "path": "/project",
    },
    "pages/login.html": {
        "robots": "noindex,nofollow",
        "title": "Войти — CLIPFENDER",
        "description": "Вход и регистрация в ClipFender для синхронизации избранного, коллекций и фильтров.",
        "path": "/login",
    },
    "pages/library.html": {
        "robots": "noindex,nofollow",
        "title": "Моя библиотека — CLIPFENDER",
        "description": "Избранное, коллекции, история поиска и сохранённые фильтры ClipFender.",
        "path": "/library",
    },
    "pages/admin.html": {
        "robots": "noindex,nofollow",
        "title": "Админ-панель — CLIPFENDER",
        "description": "Закрытая операционная панель ClipFender.",
        "path": "/admin",
    },
    "pages/privacy.html": {
        "title": "Политика конфиденциальности — CLIPFENDER",
        "description": "Политика конфиденциальности ClipFender: какие данные собираются, зачем используются и как удалить данные.",
        "path": "/privacy",
    },
    "pages/terms.html": {
        "title": "Условия использования — CLIPFENDER",
        "description": "Условия использования сервиса ClipFender и правила работы с пользовательским аккаунтом и материалами.",
        "path": "/terms",
    },
    "pages/copyright.html": {
        "title": "Авторские права и жалобы — CLIPFENDER",
        "description": "Информация об авторских правах, источниках YouTube-материалов и порядке отправки жалоб в ClipFender.",
        "path": "/copyright",
    },
    "pages/404.html": {
        "robots": "noindex,nofollow",
        "title": "404 — CLIPFENDER",
        "description": "Запрошенная страница не найдена в хрониках ClipFender.",
        "path": "/404",
    },
}


def _base_url(request: Request) -> str:
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    return str(request.base_url).rstrip("/")


def _public_url(request: Request, path: str) -> str:
    return urljoin(_base_url(request) + "/", path.lstrip("/"))


def _resolve_og_image(request: Request, template_name: str, context: dict) -> str:
    explicit = context.get("og_image")
    if explicit:
        return str(explicit)

    character = context.get("character")
    if isinstance(character, dict) and character.get("image"):
        return _public_url(request, str(character["image"]))

    if template_name == "pages/video.html":
        import re
        video_id = str(request.query_params.get("id", "")).strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    return _public_url(request, "/static/assets/meta/clipfender-og-1200x630.jpg")


def _seo_context(request: Request, template_name: str, context: dict | None = None) -> dict:
    context = context or {}
    meta = dict(SEO_PAGES.get(template_name, {
        "title": "CLIPFENDER",
        "description": "ClipFender — поиск материалов для видеомонтажа.",
        "path": request.url.path or "/",
        "robots": "index,follow,max-image-preview:large",
    }))
    canonical = _public_url(request, meta["path"])
    image = _resolve_og_image(request, template_name, context)
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": meta["title"],
        "description": meta["description"],
        "url": canonical,
        "image": image,
        "isPartOf": {
            "@type": "WebSite",
            "name": "CLIPFENDER",
            "url": _base_url(request) + "/",
        },
    }
    return {
        "page_meta": meta,
        "canonical_url": canonical,
        "og_image": image,
        "seo_json": json.dumps(schema, ensure_ascii=False),
        "analytics_enabled": bool(os.getenv("PLAUSIBLE_DOMAIN", "").strip()),
        "plausible_domain": os.getenv("PLAUSIBLE_DOMAIN", "").strip(),
        "plausible_script_url": os.getenv("PLAUSIBLE_SCRIPT_URL", "https://plausible.io/js/script.js").strip(),
    }


def render_page(request: Request, template_name: str, *, status_code: int = 200, **context):
    payload = {"request": request, **_seo_context(request, template_name, context), **context}
    return templates.TemplateResponse(request=request, name=template_name, context=payload, status_code=status_code)
