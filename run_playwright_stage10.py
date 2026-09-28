from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT = Path('/mnt/data/stage10_work')
SERVER = 'http://127.0.0.1:8765'

idea_payload = {
    'ok': True, 'status': 'ok', 'query': 'battle', 'film': 'Game of Thrones',
    'mood': 'tension', 'tempo': 'fast', 'genre': 'action', 'character': 'Джон Сноу',
    'scenario_query': 'Джон Сноу Game of Thrones battle action battle',
    'material_search': {'performed': True, 'source': 'youtube', 'loaded': 12},
    'candidate_total': 12,
    'note': 'Сценарий только из реальных материалов.',
    'stages': [
        {'key': 'intro', 'number': '01', 'label': 'INTRO', 'title': 'ИНТРО', 'description': 'Вход', 'search_focus': 'cinematic · dialogue', 'items': [{'video_id': '1', 'title': 'Jon Snow Intro', 'source': 'Test', 'url': 'https://www.youtube.com/watch?v=1', 'thumbnail': '', 'duration': '0:30', 'timecode': '00:00–00:30', 'edit_suitability_score': 88, 'score_estimated': False, 'why': 'выбрано под жанр «экшн» и персонажа «Джон Сноу»'}]},
        {'key': 'build_up', 'number': '02', 'label': 'BUILD-UP', 'title': 'НАРАСТАНИЕ', 'description': 'Нарастание', 'search_focus': 'tension · movement', 'items': [{'video_id': '2', 'title': 'Jon Snow Build', 'source': 'Test', 'url': 'https://www.youtube.com/watch?v=2', 'thumbnail': '', 'duration': '0:40', 'timecode': '00:00–00:40', 'edit_suitability_score': 86, 'score_estimated': False, 'why': 'выбрано под жанр «экшн» и персонажа «Джон Сноу»'}]},
        {'key': 'climax', 'number': '03', 'label': 'CLIMAX', 'title': 'КУЛЬМИНАЦИЯ', 'description': 'Пик', 'search_focus': 'action · epic', 'items': [{'video_id': '3', 'title': 'Jon Snow Battle', 'source': 'Test', 'url': 'https://www.youtube.com/watch?v=3', 'thumbnail': '', 'duration': '0:50', 'timecode': '00:00–00:50', 'edit_suitability_score': 94, 'score_estimated': False, 'why': 'выбрано под жанр «экшн» и персонажа «Джон Сноу»'}]},
        {'key': 'outro', 'number': '04', 'label': 'OUTRO', 'title': 'КОНЦОВКА', 'description': 'Завершение', 'search_focus': 'cinematic · emotional', 'items': [{'video_id': '4', 'title': 'Jon Snow Outro', 'source': 'Test', 'url': 'https://www.youtube.com/watch?v=4', 'thumbnail': '', 'duration': '0:35', 'timecode': '00:00–00:35', 'edit_suitability_score': 89, 'score_estimated': False, 'why': 'выбрано под жанр «экшн» и персонажа «Джон Сноу»'}]},
    ]
}
search_payload = {
    'ok': True, 'query': 'Джейми Ланнистер', 'film': 'Game of Thrones', 'filtered_total': 1,
    'results': [{'id': 'r1', 'title': 'Jaime scene', 'channel': 'Test Channel', 'thumbnail': '', 'url': 'https://www.youtube.com/watch?v=r1', 'duration': '0:42', 'edit_suitability_score': 90, 'score_estimated': False}]
}


raw = __import__('urllib.request', fromlist=['urlopen']).urlopen(SERVER + '/search?mode=idea').read().decode('utf-8')
import re
css = (ROOT / 'frontend/css/stage8-idea.css').read_text(encoding='utf-8')
raw = re.sub(r'<link[^>]+rel="stylesheet"[^>]*>', '', raw, flags=re.I)
raw = re.sub(r'<script[^>]+src="[^"]+"[^>]*></script>', '', raw, flags=re.I)
raw = raw.replace('</head>', f'<style>{css}</style></head>', 1)
js = (ROOT / 'frontend/js/stage8-idea.js').read_text(encoding='utf-8')

with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=b.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append('pageerror:'+str(e)))
    page.on('console',lambda m:errors.append('console:'+m.text) if m.type=='error' else None)

    # Browser policy blocks loopback navigation here, so load the real server markup into a DOM harness.
    fetch_stub = """<script>window.fetch=async function(url){url=String(url);if(url.includes('/api/edit-idea'))return new Response(JSON_PAYLOAD_IDEA,{status:200,headers:{'Content-Type':'application/json'}});if(url.includes('/api/search'))return new Response(JSON_PAYLOAD_SEARCH,{status:200,headers:{'Content-Type':'application/json'}});return new Response('',{status:404})};</script>"""
    fetch_stub = fetch_stub.replace('JSON_PAYLOAD_IDEA', json.dumps(json.dumps(idea_payload, ensure_ascii=False)))
    fetch_stub = fetch_stub.replace('JSON_PAYLOAD_SEARCH', json.dumps(json.dumps(search_payload, ensure_ascii=False)))
    raw_test=raw.replace('</head>',fetch_stub+'</head>',1)
    page.set_content(raw_test,wait_until='domcontentloaded')
    js_browser=js.replace('window.location.origin','"http://example.test"')
    js_browser=js_browser.replace("  document.addEventListener('DOMContentLoaded', () => {\n    setupHome();\n    setupSearchPage();\n  });","  setupHome();\n  setupSearchPage();")
    js_browser=js_browser.replace("window.history.pushState({}, '', next);","/* history.pushState omitted in DOM harness */")
    js_browser=js_browser.replace("window.history.replaceState({}, '', next);","/* history.replaceState omitted in DOM harness */")
    page.add_script_tag(content=js_browser)
    page.wait_for_timeout(250)

    assert page.locator('#cf8Genre').is_visible()

    page.locator('[data-cf-mode="search"]').click(); page.wait_for_timeout(80)
    assert page.locator('#cf8Genre').locator('xpath=..').get_attribute('hidden') == ''
    assert page.locator('#cf8Title').count() == 1 and page.locator('#cf8Title').inner_text() == 'Полноэкранный поиск материалов'
    page.locator('[data-cf-mode="idea"]').click(); page.wait_for_timeout(80)
    assert page.locator('#cf8Genre').locator('xpath=..').get_attribute('hidden') is None

    page.get_by_role('button',name='ДЖЕЙМИ ЛАННИСТЕР').click(); page.wait_for_timeout(50)
    assert page.locator('#cf8Query').input_value() == 'Джейми Ланнистер'
    page.get_by_role('button',name='БИТВА').click(); page.wait_for_timeout(50)
    assert page.locator('#cf8Query').input_value() == 'Битва'

    page.locator('#cf8Character').fill('Джон Сноу')
    page.locator('#cf8Genre').select_option('action')
    page.locator('#cf8Film').fill('Game of Thrones')
    page.locator('#cf8Query').fill('battle')
    page.locator('#cf8Mood').select_option('tension')
    page.locator('#cf8Tempo').select_option('fast')
    page.get_by_role('button',name='НАЙТИ').click(); page.wait_for_timeout(120)
    assert page.locator('.cf8-stage').count()==4
    assert page.locator('.cf8-stage-card').count()==4
    assert page.locator('.cf8-stage__connector').count()==4
    assert 'Джон Сноу' in page.locator('.cf8-scenario-head h2').inner_text()

    page.evaluate('window.__printCalled=false; window.print=()=>window.__printCalled=true')
    page.get_by_role('button',name='↓ СКАЧАТЬ РАСКАДРОВКУ').click()
    assert page.evaluate('window.__printCalled') is True

    page.locator('[data-cf-mode="search"]').click(); page.wait_for_timeout(50)
    page.locator('#cf8Query').fill('Джейми Ланнистер')
    page.get_by_role('button',name='НАЙТИ').click(); page.wait_for_timeout(100)
    assert page.locator('.cf8-card-actions a').nth(0).get_attribute('href')=='https://www.youtube.com/watch?v=r1'
    assert page.locator('.cf8-card-actions a').nth(1).get_attribute('href').startswith('/archive?q=')
    assert page.locator('[data-cf-hard-nav]').filter(has_text='АРХИВ').count()>=1

    page.locator('[data-cf-mode="idea"]').click(); page.wait_for_timeout(50)
    page.get_by_role('button',name='✦ СЛУЧАЙНАЯ ИДЕЯ').click(); page.wait_for_timeout(120)
    assert page.locator('#cf8Film').input_value()=='Game of Thrones'
    assert page.locator('#cf8Character').input_value() in {'Джон Сноу','Джейми Ланнистер','Дейенерис Таргариен','Тирион Ланнистер','Арья Старк','Серсея Ланнистер'}

    from urllib.request import urlopen
    with urlopen(SERVER + '/archive') as response:
        assert response.status == 200

    print('BUTTON_REPORT')
    print('ordinary / idea switch: PASS')
    print('archive link/route: PASS')
    print('tags Jamie / Battle: PASS')
    print('find: PASS')
    print('open YouTube: PASS (href verified)')
    print('open archive: PASS (href + /archive 200)')
    print('download storyboard: PASS (window.print invoked)')
    print('random idea: PASS')
    print('genre + character: PASS')
    print('storyboard stages/connectors: PASS')
    print('browser errors:',errors)
    b.close()
