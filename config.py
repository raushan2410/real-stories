import os

# ─── Google Sheets config ────────────────────────────────────────────────────
CSV_SHEET_ID = os.getenv("CSV_SHEET_ID")
CSV_GID      = os.getenv("CSV_GID")
CSV_URL      = (
    f"https://docs.google.com/spreadsheets/d/{CSV_SHEET_ID}"
    f"/export?format=csv&gid={CSV_GID}"
)

# ─── WhatsApp / WAHA config ──────────────────────────────────────────────────
CHAT_ID      = os.getenv("CHAT_ID")
WAHA_API_URL = os.getenv("WAHA_API_URL")

# ─── Local file paths ────────────────────────────────────────────────────────
# TEMPLATE_PATH = os.getenv("TEMPLATE_PATH")
SA_KEY_FILE   = os.getenv("SA_KEY_FILE")

# ─── Font settings ───────────────────────────────────────────────────────────
FONT_PATH = os.getenv("FONT_PATH")
FONT_SIZE = int(os.getenv("FONT_SIZE", "48"))

# ─── Text layout settings ────────────────────────────────────────────────────
TEXT_X_PADDING = int(os.getenv("TEXT_X_PADDING", "50"))
TEXT_Y_START   = int(os.getenv("TEXT_Y_START", "200"))
LINE_SPACING   = int(os.getenv("LINE_SPACING", "10"))

# ─── Retry / logging ─────────────────────────────────────────────────────────
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))
LOG_FILE    = os.getenv("LOG_FILE", "")

# ─── Message description / caption ────────────────────────────────────────────
DESCRIPTION_TEMPLATE = os.getenv(
    "DESCRIPTION_TEMPLATE",
    "{title_line}\n\n━━━━━━━━━━━━━━━━━━━━━━━\n{story_block}"
)
