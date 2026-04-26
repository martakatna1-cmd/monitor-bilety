import time
import logging
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN   = "8406145637:AAH9sZoexIVZ-HvjJPHZ4r9shPBNN8O0NCQ"
TELEGRAM_CHAT_ID = "8604163513"

THEATRES = [
    {
        "name": "Teatr Narodowy",
        "url": "https://bilety.narodowy.pl/",
        "keywords": ["wybierz termin", "wybierz bilety", "do koszyka"]
    },
    {
        "name": "Teatr Wielki Opera Narodowa",
        "url": "https://butik.teatrwielki.pl/rezerwacja/termin.html",
        "keywords": ["kup bilet", "rezerwacja/miejsca"]
    }
]

UNAVAILABLE_KEYWORDS = [
    "brak biletów",
    "wyprzedane",
    "brak wolnych miejsc",
    "sold out",
    "brak miejsc"
]

INTERVAL_SEC = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        log.info("Alert Telegram wysłany.")
        return True
    except Exception as e:
        log.error(f"Blad Telegram: {e}")
        return False

def check_with_browser(url, keywords):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000, wait_until="networkidle")
            content = page.content().lower()
            browser.close()

            found_available   = [kw for kw in keywords            if kw in content]
            found_unavailable = [kw for kw in UNAVAILABLE_KEYWORDS if kw in content]

            if found_available and not found_unavailable:
                return {"status": "available", "keywords": found_available}
            elif found_unavailable and not found_available:
                return {"status": "unavailable"}
            elif found_available and found_unavailable:
                return {"status": "available", "keywords": found_available}
            else:
                return {"status": "unknown"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def format_alert(theatre_name, url, keywords):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    kw  = ", ".join(keywords)
    return (
        f"🎭 <b>BILETY DOSTEPNE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 {theatre_name}\n"
        f"🕐 {now}\n"
        f"🔗 {url}\n"
        f"✅ Znalezione: <i>{kw}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👉 Kup teraz zanim znikna!"
    )

def main():
    log.info("START — Monitor biletow")
    send_telegram(
        f"🤖 <b>Monitor uruchomiony!</b>\n"
        f"Monitoruje {len(THEATRES)} teatry.\n"
        f"Sprawdzam co {INTERVAL_SEC} sekund."
    )

    alert_sent  = {t["url"]: False for t in THEATRES}
    last_status = {t["url"]: None  for t in THEATRES}
    check_count = 0

    while True:
        check_count += 1
        log.info(f"Sprawdzenie #{check_count}")

        for theatre in THEATRES:
            url      = theatre["url"]
            name     = theatre["name"]
            keywords = theatre["keywords"]

            result = check_with_browser(url, keywords)
            status = result.get("status")

            if status == "available":
                log.info(f"BILETY DOSTEPNE: {name}")
                if not alert_sent[url]:
                    send_telegram(format_alert(name, url, result.get("keywords", [])))
                    alert_sent[url] = True

            elif status == "unavailable":
                log.info(f"Brak biletow: {name}")
                if alert_sent[url] and last_status[url] == "available":
                    send_telegram(f"ℹ️ Bilety znow niedostepne:\n🏛 {name}")
                alert_sent[url] = False

            elif status == "error":
                log.warning(f"Blad: {result.get('detail')} — {name}")

            elif status == "unknown":
                log.warning(f"Nieznany status: {name}")

            last_status[url] = status

        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()
