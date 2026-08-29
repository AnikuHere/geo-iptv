import os
import re
import sys
import ssl
import logging
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from playwright.sync_api import sync_playwright

# Create nested logs directory: logs/logsnewstyle/
LOG_DIR = os.path.join("logs", "logsnewstyle")
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_filename(directory):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    existing_logs = [f for f in os.listdir(directory) if f.endswith(".log")]
    next_index = len(existing_logs) + 1
    return os.path.join(directory, f"{next_index}_{timestamp}.log")

LOG_FILE = get_log_filename(LOG_DIR)

# Configure verbose logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
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

def log_detailed_error(source_name, friendly_msg, exc=None, snippet=None):
    logging.error("=" * 80)
    logging.error(f"[DETAILED DIAGNOSTIC FAILURE: {source_name}]")
    logging.error(f"  ├─ Summary: {friendly_msg}")
    if exc:
        logging.error(f"  ├─ Exception Type: {type(exc).__name__}")
        logging.error(f"  ├─ Exception Message: {str(exc)}")
        logging.error("  ├─ Stack Trace:")
        for line in traceback.format_exception(type(exc), exc, exc.__traceback__):
            for subline in line.rstrip().split("\n"):
                logging.error(f"  │    {subline}")
    if snippet:
        logging.error(f"  └─ Snippet/Context: {snippet}")
    logging.error("=" * 80)

def fetch_setanta_block():
    logging.info("--> [STEP] Fetching Setanta Sports 3 from IPTV-ORG...")
    try:
        req = urllib.request.Request(IPTV_ORG_URL, headers=HEADERS)
        logging.debug(f"HTTP GET Request target: {IPTV_ORG_URL}")
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            logging.debug(f"Received HTTP response status {resp.status}, content length: {len(content)} bytes")
        
        pattern = r'(#EXTINF:-1 tvg-id="(?:SetantaSports3\.ge@SD|setanta3)"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+)'
        match = re.search(pattern, content)
        if match:
            block = match.group(1).strip()
            logging.info("Successfully extracted Setanta Sports 3 block.")
            return re.sub(r'tvg-id="[^"]+"', 'tvg-id="setanta3"', block)
        else:
            log_detailed_error("Setanta", "Channel block missing in target M3U string", snippet=content[:500])
            return None
    except Exception as e:
        log_detailed_error("Setanta", "HTTP execution failure during download", exc=e)
    return None

def fetch_mar_tv_streams():
    logging.info(f"--> [STEP] Launching batch Playwright scraper for {len(MAR_TV_TARGETS)} channels...")
    scraped_urls = {}

    try:
        with sync_playwright() as p:
            logging.debug("Launching Playwright Chromium instance with anti-detection flags...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--disable-web-security",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 720}
            )

            captured_stream_url = None
            current_channel_id = None
            request_history = []

            def handle_global_request(request):
                nonlocal captured_stream_url
                url = request.url
                request_history.append(f"[{request.method}] {url}")
                
                # Intercept m3u8 or media manifests
                if ".m3u8" in url or "playlist" in url or "master" in url:
                    logging.debug(f"Network intercept detected candidate stream URL: {url}")
                    if current_channel_id != "pirveliarxi" and ("gpb-1tv" in url or "gpb" in url):
                        logging.warning(f"  └─ Ignored fallback Pirveli Arxi stream for {current_channel_id}")
                        return
                    if not captured_stream_url and ".m3u8" in url:
                        captured_stream_url = url
                        logging.info(f"  ★ Successfully captured stream URL for {current_channel_id}: {url}")

            context.on("request", handle_global_request)

            for channel_id, page_url in MAR_TV_TARGETS.items():
                captured_stream_url = None
                current_channel_id = channel_id
                request_history.clear()
                
                logging.info(f"Processing channel [{channel_id}] -> {page_url}")
                page = context.new_page()

                try:
                    logging.debug(f"[{channel_id}] Navigating page...")
                    response = page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                    logging.debug(f"[{channel_id}] Page loaded with status: {response.status if response else 'N/A'}")
                    
                    page.wait_for_timeout(2000)

                    # Trigger viewport click to activate players requiring interaction
                    logging.debug(f"[{channel_id}] Performing force mouse click at (640, 360)")
                    page.mouse.click(640, 360)

                    # Traverse parent DOM and iframe contexts to trigger play elements
                    frames = page.frames
                    logging.debug(f"[{channel_id}] Found {len(frames)} frames on target page")
                    for index, frame in enumerate(frames):
                        logging.debug(f"[{channel_id}] Inspecting frame #{index}: {frame.url}")
                        selectors = ["video", ".play-btn", "#player", "iframe", ".vjs-big-play-button"]
                        for selector in selectors:
                            try:
                                if frame.locator(selector).count() > 0:
                                    logging.debug(f"[{channel_id}] Triggering click on '{selector}' inside frame #{index}")
                                    frame.locator(selector).first.click(force=True, timeout=1000)
                                    break
                            except Exception as click_err:
                                logging.debug(f"[{channel_id}] Click attempt failed on selector '{selector}': {click_err}")

                    page.wait_for_timeout(4000)

                except Exception as e:
                    log_detailed_error(channel_id, "Browser execution or navigation exception caught", exc=e)

                if captured_stream_url:
                    scraped_urls[channel_id] = captured_stream_url
                else:
                    # Capture debug screenshot for visual verification
                    screenshot_path = os.path.join(LOG_DIR, f"debug_{channel_id}.png")
                    try:
                        page.screenshot(path=screenshot_path)
                        logging.warning(f"  └─ Saved failure screenshot to: {screenshot_path}")
                    except Exception as ss_err:
                        logging.error(f"  └─ Failed to capture screenshot: {ss_err}")

                    history_snippet = "\n".join(request_history[-25:]) if request_history else "No requests recorded"
                    log_detailed_error(
                        channel_id, 
                        "No .m3u8 network request detected during execution sequence.", 
                        exc=RuntimeError("StreamCaptureTimeout"),
                        snippet=f"Recent Network Request History:\n{history_snippet}"
                    )

                page.close()

            browser.close()
    except Exception as e:
        log_detailed_error("PlaywrightScraper", "Critical failure launching or running Playwright browser context", exc=e)
        
    return scraped_urls

def update_my_playlist():
    setanta_block = fetch_setanta_block()
    mar_tv_streams = fetch_mar_tv_streams()

    logging.info("--> [STEP] Updating local M3U file contents...")
    try:
        with open(MY_M3U_FILE, 'r', encoding='utf-8') as f:
            my_content = f.read()
        logging.debug(f"Loaded existing M3U file '{MY_M3U_FILE}' ({len(my_content)} bytes)")
    except Exception as e:
        log_detailed_error("FileIO", f"Target playlist '{MY_M3U_FILE}' could not be read", exc=e)
        sys.exit(1)

    updated = False

    if setanta_block:
        existing_setanta = r'#EXTINF:-1 tvg-id="setanta3"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+'
        if re.search(existing_setanta, my_content):
            my_content = re.sub(existing_setanta, setanta_block, my_content)
            updated = True
            logging.info("Updated Setanta Sports 3 entry in local M3U.")
        else:
            logging.warning("Setanta Sports 3 regex anchor target was not found in local M3U file.")

    for channel_id, stream_url in mar_tv_streams.items():
        pattern = rf'(#EXTINF:-1 tvg-id="{channel_id}"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)*)[^\n]+'
        if re.search(pattern, my_content):
            my_content = re.sub(pattern, rf'\g<1>{stream_url}', my_content)
            updated = True
            logging.info(f"Updated channel URL block for: {channel_id}")
        else:
            logging.warning(f"Failed to match target tvg-id=\"{channel_id}\" in local {MY_M3U_FILE}")

    if updated:
        try:
            with open(MY_M3U_FILE, 'w', encoding='utf-8') as f:
                f.write(my_content)
            logging.info(f"★ File write successful! Saved changes to {MY_M3U_FILE}.")
        except Exception as e:
            log_detailed_error("FileIO", f"Failed to write updated content back to '{MY_M3U_FILE}'", exc=e)
    else:
        logging.info("No playlist file updates were performed.")

if __name__ == "__main__":
    logging.info("================================================================================")
    logging.info(f"=== SCRIPT EXECUTION STARTED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    logging.info(f"=== LOG TARGET: {LOG_FILE} ===")
    logging.info("================================================================================")
    
    try:
        update_my_playlist()
    except Exception as fatal_err:
        log_detailed_error("MAIN_EXECUTION", "Unhandled exception terminated execution", exc=fatal_err)
    
    logging.info("================================================================================")
    logging.info("=== SCRIPT EXECUTION COMPLETED ===")
    logging.info("================================================================================")
