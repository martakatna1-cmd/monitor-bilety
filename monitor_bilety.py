"""
=======================================================
  MONITOR BILETÓW — TEATR NARODOWY W WARSZAWIE
=======================================================
Skrypt monitoruje dostępność biletów na bilety.narodowy.pl
i wysyła alert na Telegram gdy pojawią się nowe miejsca.

WYMAGANIA:
  pip install requests beautifulsoup4

KONFIGURACJA: uzupełnij sekcję poniżej (3 wartości)
=======================================================
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime

# ─────────────────────────────────────────
#   KONFIGURACJA — WYPEŁNIJ TO
# ─────────────────────────────────────────

TELEGRAM_TOKEN   = "8406145637:AAH9sZoexIVZ-HvjJPHZ4r9shPBNN8O0NCQ"
TELEGRAM_CHAT_ID = "8604163513"

# Link do konkretnego spektaklu na bilety.narodowy.pl
SPECTACLE_URLS = [
    "https://bilety.narodowy.pl/",
    "https://butik.teatrwielki.pl/rezerwacja/termin.html"
]

# Co ile sekund sprawdzać
INTERVAL_SEC = 30

# Słowa kluczowe oznaczające DOSTĘPNOŚĆ biletu
AVAILABLE_KEYWORDS = [
    "wybierz termin",
    "wybierz bilety",
    "do koszyka",
    "kup bilet"
]

# Słowa kluczowe oznaczające BRAK biletów
UNAVAILABLE_KEYWORDS = [
    "brak biletów",
    "wyprzedane",
    "brak wolnych miejsc",
    "sold out"
]

# ─────────────────────────────────────────
#   LOGOWANIE
# ─────────────────────────────────────────

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

# ─────────────────────────────────────────
#   FUNKCJE
# ─────────────────────────────────────────

def send_telegram(message: str) -> bool:
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


def check_availability(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
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


def format_alert(result: dict, url: str) -> str:
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


# ─────────────────────────────────────────
#   GŁÓWNA PĘTLA
# ─────────────────────────────────────────

def main():
    log.info("=" * 50)
    log.info("  START — Monitor biletow Teatr Narodowy")
    log.info(f"  URL: {SPECTACLE_URL}")
    log.info(f"  Interwal: co {INTERVAL_SEC} sekund")
    log.info("=" * 50)

    send_telegram(
        f"🤖 <b>Monitor uruchomiony!</b>\n"
        f"Monitoruje: {SPECTACLE_URL}\n"
        f"Sprawdzam co {INTERVAL_SEC} sekund. Czekam na bilety..."
    )

    last_status = None
    alert_sent = False
    check_count = 0

    while True:
        check_count += 1
        log.info(f"Sprawdzenie #{check_count}...")

        for url in SPECTACLE_URLS:
    result = check_availability(url)
    status = result.get("status")

        if status == "available":
            log.info(f"BILETY DOSTEPNE! Slowa: {result.get('keywords')}")
            if not alert_sent:
                send_telegram(format_alert(result, SPECTACLE_URL))
                alert_sent = True

        elif status == "unavailable":
            log.info("Brak biletow — czekam...")
            if alert_sent and last_status == "available":
                send_telegram("ℹ️ Bilety znow niedostepne. Monitoruje dalej...")
            alert_sent = False

        elif status == "error":
            log.warning(f"Blad pobierania strony: {result.get('detail')}")
            if check_count == 1:
                send_telegram(f"⚠️ Problem z polaczeniem. Sprawdz URL: {SPECTACLE_URL}")

        elif status == "unknown":
            log.warning("Nieznany status strony.")
            if check_count == 1:
                send_telegram(
                    f"⚠️ Strona zaladowana, ale brak znanych slow kluczowych.\n"
                    f"Moze trzeba dostosowac slowa w skrypcie."
                )

        last_status = status
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
