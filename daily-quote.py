#!/usr/bin/env python3
import os
import io
import csv
import time
import random
import base64
import logging
import requests

from PIL import Image, ImageDraw, ImageFont
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime

import config

# ─── Setup logging ────────────────────────────────────────────────────────────
if config.LOG_FILE:
    logging.basicConfig(
        filename=config.LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
else:
    logging.basicConfig(
        # no filename → logs to stdout
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )




# ─── Utility: retry decorator ─────────────────────────────────────────────────
def with_retry(fn, retries=None, delay=None, **kwargs):
    retries = retries or config.RETRY_COUNT
    delay = delay or config.RETRY_DELAY
    for attempt in range(1, retries + 1):
        try:
            return fn(**kwargs)  # Directly pass kwargs to the function
        except Exception as e:
            logging.warning(f"Attempt {attempt}/{retries} for {fn.__name__} failed: {str(e)}")
            if attempt == retries:
                logging.error(f"All {retries} retries for {fn.__name__} exhausted.")
                raise
            time.sleep(delay)

# ─── Validation at startup ────────────────────────────────────────────────────
def validate_environment():
    file_paths = [config.SA_KEY_FILE, config.FONT_PATH]
    missing_files = [path for path in file_paths if not os.path.isfile(path)]
    if missing_files:
        raise FileNotFoundError(f"Required file(s) not found: {missing_files}")

    # Validate environment variables
    required_vars = [
        ("CSV_SHEET_ID", config.CSV_SHEET_ID),
        ("CHAT_ID", config.CHAT_ID),
        ("WAHA_API_URL", config.WAHA_API_URL)
    ]
    missing_vars = [name for name, value in required_vars if not value]
    
    if missing_vars:
        raise ValueError(f"Required environment variables missing: {missing_vars}")

# ─── Fetch & parse the sheet as CSV ──────────────────────────────────────────
def fetch_sheet_rows_via_api():
    svc = get_sheets_service()
    # Read columns A:C from row 1 onward
    range_ = f"Sheet1!A1:C"
    result = with_retry(
        svc.spreadsheets().values().get,
        spreadsheetId=config.CSV_SHEET_ID,
        range=range_
    ).execute()

    values = result.get("values", [])
    if not values or values[0] != ["Story", "Title", "Used"]:
        raise ValueError(f"Unexpected header row: {values[:1]}")
    # Each subsequent row is [Quote, Author, Used]
    rows = []
    for row in values[1:]:
        # pad missing columns
        story, title, used = (row + ["", "", ""])[:3]
        rows.append({"Story": story, "Title": title, "Used": used})
    return rows


# ─── Pick a random unused quote ───────────────────────────────────────────────
def select_unused_quote(rows):
    unused = [(i, r) for i, r in enumerate(rows)
              if r.get("Used", "").strip().lower() == "no"]
    if not unused:
        raise RuntimeError("No unused story available.")
    return unused[0]   # return first unused quote

# ─── Sheets API client and update ────────────────────────────────────────────
def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        config.SA_KEY_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)


# ─── Mark a quote as used in the sheet ───────────────────────────────────────
def mark_quote_used(row_idx):
    service = get_sheets_service()
    sheet_row = row_idx + 2  # account for header
    range_name = f"Sheet1!C{sheet_row}"
    
    # Get today's date in YYYY-MM-DD format
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [{
            "range": range_name,
            "values": [[today_date]] 
        }]
    }
    
    try:
        logging.info(f"Marking row {row_idx} as used with date {today_date}")
        response = service.spreadsheets().values().batchUpdate(
            spreadsheetId=config.CSV_SHEET_ID,
            body=body
        ).execute()
        
        # logging.info(f"Google Sheets update response: {response}")
        return True
        
    except HttpError as e:
        logging.error(f"Google Sheets API error: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return False

# ─── Render the image with Pillow ────────────────────────────────────────────
# def render_quote_image(quote, author):
#     img = Image.open(config.TEMPLATE_PATH).convert("RGB")
#     draw = ImageDraw.Draw(img)
#     font = ImageFont.truetype(config.FONT_PATH, config.FONT_SIZE)
#     max_w = img.width - 2 * config.TEXT_X_PADDING

#     # Word-wrap using draw.textbbox()
#     words, lines, current = quote.split(), [], ""
#     for w in words:
#         test = (current + " " + w).strip()
#         # get bounding box of the test string
#         bbox = draw.textbbox((0, 0), test, font=font)
#         test_w = bbox[2] - bbox[0]
#         if test_w <= max_w:
#             current = test
#         else:
#             lines.append(current)
#             current = w
#     lines.append(current)

#     # Draw each line centered
#     y = config.TEXT_Y_START
#     for line in lines:
#         bbox = draw.textbbox((0, 0), line, font=font)
#         line_w = bbox[2] - bbox[0]
#         line_h = bbox[3] - bbox[1]
#         x = (img.width - line_w) // 2
#         draw.text((x, y), line, font=font, fill="white")
#         y += line_h + config.LINE_SPACING

#     # Draw author below
#     auth_text = f"— {author}"
#     bbox = draw.textbbox((0, 0), auth_text, font=font)
#     auth_w = bbox[2] - bbox[0]
#     auth_h = bbox[3] - bbox[1]
#     x = (img.width - auth_w) // 2
#     draw.text((x, y + config.LINE_SPACING), auth_text, font=font, fill="white")

#     # Encode to JPEG bytes
#     buf = io.BytesIO()
#     img.save(buf, format="JPEG")
#     return buf.getvalue()



# ─── Send to WAHA endpoint ───────────────────────────────────────────────────
def send_to_waha(story, title):
    """Encodes and posts the image to WAHA with a caption."""
    # b64 = base64.b64encode(image_bytes).decode()
    # 1) Convert title to bold‐Unicode
    # fancy_title = to_bold_unicode(title.upper())
    #if title has spaces in the end, remove it
    title = title.strip()
    if not title:
        raise ValueError("Title cannot be empty after stripping whitespace.")
    title_line  = f"`{title}`"

    # 2) Optionally italicize or use monospace for story
    story_block = f"```\n{story}\n```"

    caption = config.DESCRIPTION_TEMPLATE.format(
        title_line=title_line,
        story_block=story_block
    )

    payload = {
        "chatId": config.CHAT_ID,
        "reply_to": None,
        "text": caption,
        "linkPreview": True,
        "linkPreviewHighQuality": False,
        "session": "default"
    }

    # Call with positional fn and keyword args directly
    resp = with_retry(
        requests.post,
        url=config.WAHA_API_URL,
        json=payload,
        timeout=10
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"WAHA API error {resp.status_code}: {resp.text}")
    logging.info("Image with caption sent to WAHA.")

def get_sheet():
    try:
        rows = fetch_sheet_rows_via_api()
        idx, row = select_unused_quote(rows)
        story, title = row["Story"].strip(), row["Title"].strip()
        logging.info(f"Selected story #{idx}: {story[:30]}...")
        return story, title, idx
    
    except HttpError as e:
        logging.error(f"Google Sheets API error: {e}")
        raise RuntimeError("Failed to fetch or update story from Google Sheets.")
    
# ─── Update the sheet after sending ───────────────────────────────────────────
def update_sheet(idx):
    if not mark_quote_used(idx):
        logging.error(f"Failed to mark Story #{idx} as used in the sheet.")
    else:
        logging.info(f"Story #{idx} marked as used successfully.")

# ─── Ensure WAHA session is running ──────────────────────────────────────────
def ensure_waha_session():
    """
    Checks the default WAHA session status; if it's STOPPED, starts it.
    Relies on config.WAHA_API_URL being something like
      http://waha:3000/api/sendText
    """
    # derive the base path for sessions
    base = config.WAHA_API_URL.rsplit("/api/", 1)[0] + "/api"
    status_url = f"{base}/sessions/default"
    start_url  = f"{status_url}/start"

    try:
        r = requests.get(status_url, timeout=5)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logging.warning(f"Could not check WAHA session status: {e}")
        return  # give up; let send_to_waha handle any errors

    status = data.get("status", "").upper()
    if status == "STOPPED":
        logging.info("WAHA session is STOPPED; starting it now…")
        try:
            r2 = requests.post(start_url, timeout=5)
            r2.raise_for_status()
            logging.info("WAHA session started successfully.")
            # give WAHA a couple of seconds to spin up
            time.sleep(2)
        except Exception as e:
            logging.error(f"Failed to start WAHA session: {e}")
    else:
        logging.debug(f"WAHA session status is '{status}', no action needed.")

# ─── Main flow ───────────────────────────────────────────────────────────────
def main():
    try:
        validate_environment()
        ensure_waha_session()
        story, title, idx = get_sheet()
        # img_bytes = render_quote_image(quote, author)
        send_to_waha(story, title)
        update_sheet(idx)

    except Exception:
        logging.exception("Fatal error in daily_quote.py run.")

if __name__ == "__main__":
    main()
