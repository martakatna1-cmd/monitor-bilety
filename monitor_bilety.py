import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime

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
        "keywords": ["kup bilet", "btn--brown"]
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

def check_availability(url, keywords):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "detail": str(e)}

    content = response.text.lower()

    found_available   = [kw for kw in keywords             if kw in content]
    found_unavailable = [kw for kw in UNAVAILABLE_KEYWORDS if kw in content]

    if found_available:
        return {"status": "available", "keywords": found_available}
    elif found_unavailable:
        return {"status": "unavailable"}
    else:
        return {"status": "unknown"}

def format_alert(name, url, keywords):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    kw  = ", ".join(keywords)
    return (
        f"🎭 <b>BILETY DOSTEPNE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 {name}\n"
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

            result = check_availability(url, keywords)
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
