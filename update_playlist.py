import os
import re
import sys
import ssl
import logging
import urllib.request
from datetime import datetime

LOG_DIR = "logs_updater"
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_filename(directory):
    base_file = os.path.join(directory, "updater.log")
    if not os.path.exists(base_file):
        return base_file
    
    # Format timestamp: 12:28_17d08m26y
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

def fetch_setanta_block():
    logging.info("Fetching Setanta Sports 3 from IPTV-ORG...")
    try:
        req = urllib.request.Request(IPTV_ORG_URL, headers=HEADERS)
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
            content = resp.read().decode('utf-8')
        
        pattern = r'(#EXTINF:-1 tvg-id="(?:SetantaSports3\.ge@SD|setanta3)"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+)'
        match = re.search(pattern, content)
        if match:
            block = match.group(1).strip()
            logging.info("Setanta block retrieved successfully.")
            return re.sub(r'tvg-id="[^"]+"', 'tvg-id="setanta3"', block)
        else:
            logging.warning("Setanta pattern not matched in IPTV-ORG payload.")
            return None
    except Exception as e:
        logging.error(f"Setanta fetch failed: {e}")
        return None

def generate_gds_link():
    logging.info("Extracting GDS link from tv.mar.tv...")
    page_url = "https://tv.mar.tv/13"
    
    try:
        req = urllib.request.Request(page_url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
            html = resp.read().decode('utf-8')
        
        pattern = r'https?://[a-zA-Z0-9\.-]+\.mar\.tv/[a-f0-9]{32,64}/13[a-zA-Z0-9]*/index\.m3u8'
        match = re.search(pattern, html)
        if match:
            logging.info(f"Direct GDS stream URL matched: {match.group(0)}")
            return match.group(0)
        
        token_match = re.search(r'([a-f0-9]{64})', html)
        if token_match:
            generated = f"https://live1.mar.tv/{token_match.group(1)}/13sd/index.m3u8"
            logging.info(f"Generated GDS token stream URL: {generated}")
            return generated

        logging.warning("Could not extract video token from GDS HTML source.")
    except Exception as e:
        logging.error(f"GDS fetch failed: {e}")
        
    return None

def update_my_playlist():
    setanta_block = fetch_setanta_block()
    new_gds_url = generate_gds_link()

    if not setanta_block and not new_gds_url:
        logging.error("CRITICAL: Failed to retrieve updates for both streams. Exiting with error.")
        sys.exit(1)

    try:
        with open(MY_M3U_FILE, 'r', encoding='utf-8') as f:
            my_content = f.read()
    except FileNotFoundError:
        logging.error(f"Target M3U file '{MY_M3U_FILE}' not found.")
        sys.exit(1)

    updated = False

    if setanta_block:
        existing_setanta = r'#EXTINF:-1 tvg-id="setanta3"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+'
        if re.search(existing_setanta, my_content):
            my_content = re.sub(existing_setanta, setanta_block, my_content)
            updated = True
            logging.info("Updated Setanta entry in playlist.")

    if new_gds_url:
        gds_pattern = r'(#EXTINF:-1 tvg-id="gds"[^\n]*\n)[^\n]+'
        if re.search(gds_pattern, my_content):
            my_content = re.sub(gds_pattern, r'\g<1>' + new_gds_url, my_content)
            updated = True
            logging.info("Updated GDS entry in playlist.")

    if updated:
        with open(MY_M3U_FILE, 'w', encoding='utf-8') as f:
            f.write(my_content)
        logging.info(f"Saved changes to {MY_M3U_FILE}.")
    else:
        logging.info("Playlist already up to date. No file changes needed.")

if __name__ == "__main__":
    logging.info(f"=== UPDATE EXECUTION STARTED (Log: {os.path.basename(LOG_FILE)}) ===")
    update_my_playlist()
    logging.info("=== UPDATE EXECUTION FINISHED ===")
