import os
import re
import sys
import ssl
import logging
import urllib.request
import urllib.error
from datetime import datetime
from playwright.sync_api import sync_playwright

LOG_DIR = "logs_updater"
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_filename(directory):
    base_file = os.path.join(directory, "updater.log")
    if not os.path.exists(base_file):
        return base_file
    
    timestamp = datetime.now().strftime("%H:%M_%dd%mm%yy")
    existing_logs = [f for f in os.listdir(directory) if f.startswith("updater") and f.endswith(".log")]
    next_index = len(existing_logs) + 1
    
    return os.path.join(directory, f"updater_{next_index}_{timestamp}.log")

LOG_FILE = get_log_filename(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

IPTV_ORG_URL = "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ge.m3u"
MY_M3U_FILE = "georgia_channels.m3u"

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Mapping M3U tvg-id tags to their mar.tv page URL
MAR_TV_TARGETS = {
    "rustavi2": "https://tv.mar.tv/4",
    "maestro": "https://tv.mar.tv/5",
    "marao": "https://tv.mar.tv/12",
    "gds": "https://tv.mar.tv/13",
    "comedy": "https://tv.mar.tv/14",
    "bbb": "https://tv.mar.tv/16",
    "enkibenki": "https://tv.mar.tv/17",
    "adjaratv": "https://tv.mar.tv/19",
    "rionitv": "https://tv.mar.tv/20",
    "tv25": "https://tv.mar.tv/23",
    "tv4rustavi": "https://tv.mar.tv/24",
    "trialeti": "https://tv.mar.tv/25",
    "dardimandi": "https://tv.mar.tv/27",
    "agro": "https://tv.mar.tv/28",
    "samefo": "https://tv.mar.tv/29",
    "postv": "https://tv.mar.tv/31",
    "megatv": "https://tv.mar.tv/32",
    "qartuliarxi": "https://tv.mar.tv/33",
    "musicbox": "https://tv.mar.tv/34",
    "marneuli": "https://tv.mar.tv/37",
    "axaliformula": "https://tv.mar.tv/38",
    "o2": "https://tv.mar.tv/40",
    "guria": "https://tv.mar.tv/42",
    "imervizia": "https://tv.mar.tv/43",
    "diatv": "https://tv.mar.tv/44",
    "chveniarxi": "https://tv.mar.tv/45",
    "batumitv": "https://tv.mar.tv/46",
    "rcheuli": "https://tv.mar.tv/47",
    "gurjaani": "https://tv.mar.tv/48",
    "molitv": "https://tv.mar.tv/49",
    "mexute": "https://tv.mar.tv/50",
    "agrogaremo": "https://tv.mar.tv/51",
    "artv": "https://tv.mar.tv/52",
    "meteo24": "https://tv.mar.tv/56",
    "georgiantimes": "https://tv.mar.tv/57",
    "silkuniversal": "https://tv.mar.tv/155",
    "rugbytv": "https://tv.mar.tv/160",
    "gms": "https://tv.mar.tv/161",
    "aiatv": "https://tv.mar.tv/992",
    "batumi2": "https://tv.mar.tv/994",
    "altinfo": "https://tv.mar.tv/996",
    "parliament": "https://tv.mar.tv/997",
    "egrisi": "https://tv.mar.tv/998",
    "mzetv": "https://tv.mar.tv/999"
}

def log_detailed_error(source_name, friendly_msg, raw_code_msg, snippet=None):
    logging.error(f"[{source_name} FAILURE]")
    logging.error(f"  └─ Reason: {friendly_msg}")
    logging.error(f"  └─ Error Output: {raw_code_msg}")
    if snippet:
        logging.error(f"  └─ Snippet: {snippet}")

def fetch_setanta_block():
    logging.info("Fetching Setanta Sports 3 from IPTV-ORG...")
    try:
        req = urllib.request.Request(IPTV_ORG_URL, headers=HEADERS)
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
        
        pattern = r'(#EXTINF:-1 tvg-id="(?:SetantaSports3\.ge@SD|setanta3)"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+)'
        match = re.search(pattern, content)
        if match:
            block = match.group(1).strip()
            return re.sub(r'tvg-id="[^"]+"', 'tvg-id="setanta3"', block)
        else:
            log_detailed_error("Setanta", "Channel block missing", "Regex Pattern Match Failed")
            return None
    except Exception as e:
        log_detailed_error("Setanta", "Unexpected Execution Error", f"{type(e).__name__}: {str(e)}")
    return None

def fetch_mar_tv_streams():
    logging.info(f"Launching batch scraper for {len(MAR_TV_TARGETS)} channels on tv.mar.tv...")
    scraped_urls = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            
            for channel_id, page_url in MAR_TV_TARGETS.items():
                captured_stream_url = None
                page = context.new_page()

                def handle_request(request):
                    nonlocal captured_stream_url
                    url = request.url
                    if ".m3u8" in url:
                        # Prevent tv.mar.tv from defaulting to Pirveli Arxi for paywalled/unauth streams
                        if channel_id != "pirveliarxi" and ("gpb-1tv" in url or "gpb" in url):
                            logging.warning(f"  └─ Ignored fallback Pirveli Arxi stream for {channel_id}")
                            return
                        captured_stream_url = url

                page.on("request", handle_request)
                logging.info(f"Scraping {channel_id}...")

                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(3000)  # Wait for JS player to request stream
                except Exception as e:
                    log_detailed_error(channel_id, f"Browser timed out or failed to load.", str(e))
                
                page.close()

                if captured_stream_url:
                    logging.info(f" -> Success: {captured_stream_url}")
                    scraped_urls[channel_id] = captured_stream_url
                else:
                    log_detailed_error(channel_id, "No .m3u8 network request detected.", "PlaywrightNetworkListenerError")

            browser.close()
    except Exception as e:
        logging.error(f"Critical browser setup failure: {e}")
        
    return scraped_urls

def update_my_playlist():
    setanta_block = fetch_setanta_block()
    mar_tv_streams = fetch_mar_tv_streams()

    try:
        with open(MY_M3U_FILE, 'r', encoding='utf-8') as f:
            my_content = f.read()
    except FileNotFoundError as e:
        logging.error(f"Target playlist missing: {e}")
        sys.exit(1)

    updated = False

    # Inject Setanta
    if setanta_block:
        existing_setanta = r'#EXTINF:-1 tvg-id="setanta3"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+'
        if re.search(existing_setanta, my_content):
            my_content = re.sub(existing_setanta, setanta_block, my_content)
            updated = True

    # Inject Mar.tv streams dynamically based on tvg-id
    for channel_id, stream_url in mar_tv_streams.items():
        pattern = rf'(#EXTINF:-1 tvg-id="{channel_id}"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)*)[^\n]+'
        if re.search(pattern, my_content):
            my_content = re.sub(pattern, rf'\g<1>{stream_url}', my_content)
            updated = True
            logging.info(f"Updated M3U block for: {channel_id}")
        else:
            logging.warning(f"Failed to find tvg-id=\"{channel_id}\" in {MY_M3U_FILE}")

    if updated:
        with open(MY_M3U_FILE, 'w', encoding='utf-8') as f:
            f.write(my_content)
        logging.info(f"Saved changes to {MY_M3U_FILE}.")
    else:
        logging.info("No file changes were made.")

if __name__ == "__main__":
    logging.info(f"=== UPDATE EXECUTION STARTED ===")
    update_my_playlist()
    logging.info("=== UPDATE EXECUTION FINISHED ===")
