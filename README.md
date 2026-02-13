# BPM Bot — Telegram-бот для музыкантов

Бот переводит темп (BPM) в длительности нот в миллисекундах: основные, триоли, пунктирные.

## Быстрый старт (локально)

1. Скопируйте `.env.example` в `.env` и вставьте токен от [@BotFather](https://t.me/BotFather):

   ```
   TELEGRAM_BOT_TOKEN=ваш_токен
   ```

2. Установите зависимости и запустите:

   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

   Или дважды щёлкните по `run_bot.bat` (Windows).

3. В Telegram напишите боту `/start` и отправьте число BPM (например, `140`).

---

## Деплой на хостинг

### Вариант 1: VPS с Docker

```bash
# Клонируйте репозиторий или скопируйте файлы на сервер
cd Bot_BPM

# Создайте .env с токеном
cp .env.example .env
nano .env  # вставьте TELEGRAM_BOT_TOKEN=...

# Запустите
docker compose up -d --build
```

Бот будет работать в фоне и перезапускаться при падении.

Логи: `docker compose logs -f`  
Остановить: `docker compose down`

### Вариант 2: Railway / Render / Heroku

1. Создайте репозиторий на GitHub и загрузите файлы (кроме `.env`).
2. Подключите репозиторий к хостингу.
3. Добавьте переменную окружения `TELEGRAM_BOT_TOKEN` в настройках проекта.
4. Деплой произойдёт автоматически (Procfile и runtime.txt уже настроены).

**Railway:** https://railway.app  
**Render:** https://render.com (выберите Background Worker)  
**Heroku:** `heroku create && heroku config:set TELEGRAM_BOT_TOKEN=... && git push heroku main`

### Вариант 3: VPS без Docker

```bash
# Установите Python 3.10+
sudo apt update && sudo apt install python3 python3-pip python3-venv -y

# Скопируйте файлы на сервер и перейдите в папку
cd Bot_BPM

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt

# Создайте .env
cp .env.example .env
nano .env

# Запустите в фоне через systemd (см. ниже) или screen/tmux
python bot.py
```

#### Systemd-сервис (рекомендуется)

Создайте файл `/etc/systemd/system/bpm-bot.service`:

```ini
[Unit]
Description=BPM Telegram Bot
After=network.target

[Service]
Type=simple
User=ваш_пользователь
WorkingDirectory=/путь/к/Bot_BPM
EnvironmentFile=/путь/к/Bot_BPM/.env
ExecStart=/путь/к/Bot_BPM/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bpm-bot
sudo systemctl start bpm-bot
sudo systemctl status bpm-bot
```

---

## Структура файлов

```
Bot_BPM/
├── bot.py              # Основной код бота
├── requirements.txt    # Зависимости Python
├── .env.example        # Пример переменных окружения
├── .env                # Ваши переменные (не коммитить!)
├── .gitignore          # Исключения для git
├── Dockerfile          # Сборка Docker-образа
├── docker-compose.yml  # Запуск через Docker Compose
├── Procfile            # Для Railway/Heroku/Render
├── runtime.txt         # Версия Python для PaaS
├── run_bot.bat         # Запуск под Windows (локально)
└── README.md           # Эта документация
```

---

## Команды бота

- `/start` — приветствие и инструкция
- `/ping` — проверка работоспособности (ответит «ок»)
- Любое число — расчёт длительностей нот для этого BPM
