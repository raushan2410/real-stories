# Real Stories WhatsApp Bot

> **🚀 To see this bot in action**
> 👉 [Visit my WhatsApp Channel where I post daily stories using this bot!](https://www.whatsapp.com/channel/0029VbAocBlJENy7BDlMpL2f)

Automated WhatsApp bot to fetch inspirational real-life stories from Google Sheets and send them to your WhatsApp newsletter/channel using the WAHA HTTP API.

Deploy it using Docker with a minimal setup.

---

## ✨ Features

* Fetches stories and titles from Google Sheets
* Sends formatted WhatsApp messages using WAHA API
* Tracks used stories to avoid repeats
* Environment-based configuration
* Works manually or in scheduled mode (e.g., cron)
* Docker-based deployment

---

## 📌 Google Sheets Format

Your sheet should have:

| Story                  | Title           | Used |
| ---------------------- | --------------- | ---- |
| Some inspiring text... | Inspiring Title | No   |

* **Used** column must have `"No"` for new/unposted stories.
* The script updates it with today’s date once sent.

---

## 📂 Project Files

```
.
├── daily-quote.py         # Main script
├── config.py              # Loads config from env vars
├── requirements.txt       # Python dependencies
├── Dockerfile             # Image build config
├── docker-compose.yml     # Multi-container setup
├── .env                   # Configuration settings
├── sa-key.json            # GCP service account key
```

---

## 🔧 Configuration

Set these in your `.env`:

```
CSV_SHEET_ID=<your-sheet-id>
CSV_GID=0
CHAT_ID=120363416744523310@newsletter
WAHA_API_URL=http://waha:3000/api/sendText
SA_KEY_FILE=/app/sa-key.json
FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
FONT_SIZE=48
TEXT_X_PADDING=50
TEXT_Y_START=200
LINE_SPACING=10
RETRY_COUNT=3
RETRY_DELAY=2
```

---

## 🚀 Setup & Usage

### 1. Build Docker Image

```bash
docker build -t approval-app .
```

### 2. Start Required Services

Start WAHA (WhatsApp HTTP API):

```bash
docker compose up -d
```

This starts the `waha` service in the background.

### 3. Run the Script Manually

```bash
docker-compose run --rm app
```

This executes the bot once and cleans up the container afterward.

### 4. CronJob Alternative

To run daily or on a schedule:

```bash
0 10 * * * docker run --rm \
  --env-file /path/to/.env \
  -v /path/to/sa-key.json:/app/sa-key.json \
  approval-app
```

---

## 🧠 How It Works

1. Connects to your Google Sheet via service account
2. Picks the first unused story (Used = "No")
3. Sends it to WhatsApp using WAHA API
4. Marks the story as used with the current date

---

## 🧪 WAHA Setup

The `docker-compose.yml` handles it:

```yaml
services:
  waha:
    image: devlikeapro/waha:arm
    ports:
      - "3003:3000"
    volumes:
      - ./.sessions:/app/.sessions
    environment:
      - WAHA_LOCAL_STORE_BASE_DIR=/app/.sessions

  app:
    image: approval-app
    depends_on:
      - waha
    env_file:
      - .env
```

First-time setup may require scanning a QR code in WAHA logs to link your WhatsApp.

---

## 📚 Adding New Stories

1. Open your Google Sheet
2. Add new rows with:

   * Story text
   * Title
   * `Used` = `No`

That's all — the script handles the rest.

---

## 🔗 License

MIT

---
