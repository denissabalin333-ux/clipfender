# ClipFender Stage 15 — portrait refresh

Семь активных `*-hq.webp` заменены на новые cinematic-портреты, подготовленные из ранее сгенерированного набора в едином стиле.

Персонажи:
- Jon Snow — `frontend/assets/reference/final/jon-hq.webp`
- Jaime Lannister — `frontend/assets/reference/final/jaime-hq.webp`
- Daenerys Targaryen — `frontend/assets/reference/final/daenerys-hq.webp`
- Tyrion Lannister — `frontend/assets/reference/final/tyrion-hq.webp`
- Arya Stark — `frontend/assets/reference/final/arya-hq.webp`
- Barristan Selmy — `frontend/assets/reference/final/barristan-hq.webp`
- Cersei Lannister — `frontend/assets/reference/final/cersei-hq.webp`

## Стиль для будущих персонажей

Все следующие персонажи при ручном добавлении в каталог будут получать отдельный индивидуальный портрет в том же визуальном направлении:
- тёмное средневековое фэнтези;
- кинематографический тёпло-холодный свет;
- натуральный портрет по плечи/грудь;
- высокий локальный контраст лица и костюма;
- тёмный атмосферный фон без текста;
- бронзово-золотые акценты только как часть общего света/UI, а не как напечатанная рамка;
- единый вертикальный crop под карточку персонажа;
- исходник должен быть достаточно большим, чтобы не увеличивать маленький кадр на карточке.

Новые персонажи не создаются автоматически из случайных изображений. Для каждого нового профиля сначала должен существовать отдельный качественный portrait asset, затем он добавляется в `CHARACTER_PROFILES`.

Старые семь файлов сохранены в `_backup/stage15/` и `_archive/stage15/portrait-refresh-20260927/`. Исходный сгенерированный roster-source также сохранён в archive.
