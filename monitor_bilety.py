import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime

TELEGRAM_TOKEN   = "8406145637:AAH9sZoexIVZ-HvjJPHZ4r9shPBNN8O0NCQ"
TELEGRAM_CHAT_ID = "8604163513"

SPECTACLE_URLS = [
    "https://bilety.narodowy.pl/",
    "https://butik.teatrwielki.pl/rezerwacja/termin.html"
]

INTERVAL_SEC = 30

AVAILABLE_KEYWORDS = [
    "wybierz termin",
    "wybierz bilety",
    "do koszyka",
    "kup bilet"
]

UNAVAILABLE_KEYWORDS = [
    "brak biletów",
    "wyprzedane",
    "brak wolnych miejsc",
    "sold out",
    "brak miejsc"
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor_log.txt", encoding="utf-8")
    ]
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

def check_availability(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(separator=" ").lower()

    found_available   = [kw for kw in AVAILABLE_KEYWORDS   if kw in page_text]
    found_unavailable = [kw for kw in UNAVAILABLE_KEYWORDS if kw in page_text]

    if found_available and not found_unavailable:
        return {"status": "available", "keywords": found_available}
    elif found_unavailable:
        return {"status": "unavailable", "keywords": found_unavailable}
    else:
        return {"status": "unknown", "detail": "Nie znaleziono slow kluczowych."}

def format_alert(result, url):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    keywords = ", ".join(result.get("keywords", []))
    return (
        f"🎭 <b>BILETY DOSTEPNE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {now}\n"
        f"🔗 {url}\n"
        f"✅ Znalezione: <i>{keywords}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👉 Kup teraz zanim znikna!"
    )

def main():
    log.info("START — Monitor biletow")
    send_telegram(
        f"🤖 <b>Monitor uruchomiony!</b>\n"
        f"Monitoruje {len(SPECTACLE_URLS)} teatry.\n"
        f"Sprawdzam co {INTERVAL_SEC} sekund."
    )

    alert_sent = {}
    last_status = {}
    check_count = 0

    while True:
        check_count += 1
        log.info(f"Sprawdzenie #{check_count}")

        for url in SPECTACLE_URLS:
            result = check_availability(url)
            status = result.get("status")

            if status == "available":
                log.info(f"BILETY DOSTEPNE! {url}")
                if not alert_sent.get(url):
                    send_telegram(format_alert(result, url))
                    alert_sent[url] = True

            elif status == "unavailable":
                log.info(f"Brak biletow: {url}")
                if alert_sent.get(url) and last_status.get(url) == "available":
                    send_telegram(f"ℹ️ Bilety znow niedostepne:\n{url}")
                alert_sent[url] = False

            elif status == "error":
                log.warning(f"Blad: {result.get('detail')} — {url}")

            elif status == "unknown":
                log.warning(f"Nieznany status: {url}")

            last_status[url] = status

        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()
