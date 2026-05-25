# Catalog Agent

Агент автоматической регистрации сайта в **10 каталогах** для получения обратных ссылок.

- Веб-интерфейс (серые кнопки, таблица результатов)
- **Playwright** — регистрация и заполнение карточки
- Парсинг данных с сайта (название, описание, телефон, услуги, логотип)
- **IMAP** — коды подтверждения с почты
- **SQLite** — логины, пароли, ссылки на профиль и backlink

## Быстрый старт

```bash
cd catalog-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# отредактируйте .env (IMAP — для live-режима и реальной почты)
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Откройте http://127.0.0.1:8000 — введите URL сайта и email, нажмите **Запустить регистрацию**.

## Режимы

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DEMO_MODE` | `true` | 10 демо-форм (`static/demo/*.html`, file://) — полный цикл без капчи и без сети |
| `DEMO_MODE=false` | | Реальные URL каталогов (нужны IMAP и доработка селекторов под каждый сайт) |

## 10 каталогов (тест)

1. Yell.ru  
2. OrgPage.ru  
3. Spravker.ru  
4. AllBiz.ru  
5. List-Org.com  
6. BizOrg.su  
7. RusCatalog.org  
8. Tiuru.ru  
9. Firmika.ru  
10. Справочник №10 (demo id: `catalog10`)

## Почта (IMAP)

Для кодов подтверждения в live-режиме укажите в `.env`:

```
IMAP_HOST=imap.mail.ru
IMAP_USER=your@mail.ru
IMAP_PASSWORD=пароль_приложения
```

Для Mail.ru / Yandex используйте пароль приложения, не основной пароль.

## Структура

```
app/
  main.py          # API + веб + demo-страницы
  agent.py         # оркестратор Playwright
  scraper.py       # данные с сайта
  email_imap.py    # коды из почты
  db.py            # SQLite
  catalogs/        # адаптеры каталогов
static/            # UI
templates/         # HTML
data/              # БД (создаётся автоматически)
```

## Замечания

- Реальные каталоги меняют вёрстку и ставят капчу — адаптеры в `app/catalogs/adapters.py` дополняются под каждый сайт.
- В **demo_mode** агент читает код с страницы `#demo-code` (имитация письма).
- Скриншоты Playwright: `PLAYWRIGHT_HEADLESS=false` для отладки.
