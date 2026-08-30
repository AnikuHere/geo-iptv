import os
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Ensure the required logging directory structure exists
LOG_DIR = os.path.join("logs_updater", "logsnewstyle")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure detailed logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "playlist_update.log"), mode='w'),
        logging.StreamHandler()
    ]
)

channels = [
    {
        "name": "PosTV",
        "primary": "https://tv.mar.tv/postv",
        "backup": "https://www.televizia.org/postv/"
    },
    {
        "name": "AdjaraTV",
        "primary": "https://tv.mar.tv/adjaratv",
        "backup": "https://streaming-hls1.televizia.org/hls/adjara.m3u8" 
    },
    {
        "name": "Axali Formula",
        "primary": "https://tv.mar.tv/formulatv",
        "backup": "https://www.arxebi.live/ge/formulatv"
    },
    {
        "name": "RugbyTV",
        "primary": "https://tv.mar.tv/rugbytv",
        "backup": "https://www.arxebi.live/ge/rugbytv"
    },
    {
        "name": "ObieqtiviTV",
        "primary": "https://tv.mar.tv/obieqtivitv",
        "backup": "https://www.arxebi.live/ge/obieqtivitv"
    },
    {
        "name": "Palitranews",
        "primary": "https://tv.mar.tv/palitranewstv",
        "backup": "https://www.arxebi.live/ge/palitranewstv"
    },
    {
        "name": "GDS",
        "primary": "https://tv.mar.tv/gds",
        "backup": "https://www.arxebi.live/ge/gds"
    },
    {
        "name": "BBB",
        "primary": "https://tv.mar.tv/bastibubutv",
        "backup": "https://www.arxebi.live/ge/bastibubutv"
    },
    {
        "name": "Enkibenki",
        "primary": "https://tv.mar.tv/enkibenkitv",
        "backup": "https://www.arxebi.live/ge/enkibenkitv"
    },
    {
        "name": "KvemoKartli TV",
        "primary": "https://tv.mar.tv/kvemokartlitv",
        "backup": "https://www.arxebi.live/ge/kvemokartlitv"
    },
    {
        "name": "MaraoTV",
        "primary": "https://tv.mar.tv/maraotv",
        "backup": "https://www.arxebi.live/ge/maraotv"
    }
]

def extract_m3u8(page, url, channel_name, source_type):
    """Navigates to the URL, attempts to extract the stream, and screenshots failures."""
    if url.endswith(".m3u8"):
        logging.info(f"[{source_type}] {channel_name}: Direct link detected, skipping browser extraction.")
        return url

    logging.info(f"[{source_type}] Loading {url} for {channel_name}...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        
        with page.expect_response(lambda response: ".m3u8" in response.url, timeout=15000) as response_info:
            player = page.locator("iframe, video, .video-js, .player-container").first
            
            if player.is_visible(timeout=5000):
                box = player.bounding_box()
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            else:
                logging.warning(f"[{source_type}] {channel_name}: Player not visible on page.")
                
        stream_url = response_info.value.url
        logging.info(f"[{source_type}] {channel_name}: Stream captured successfully.")
        return stream_url

    except PlaywrightTimeoutError:
        logging.error(f"[{source_type}] {channel_name}: Timeout error. Stream failed to initialize.")
    except Exception as e:
        logging.error(f"[{source_type}] {channel_name}: Unexpected error - {e}")

    # Execution only reaches here if the extraction block fails
    filename = f"debug_{channel_name.replace(' ', '_')}_{source_type.lower()}.png"
    screenshot_path = os.path.join(LOG_DIR, filename)
    
    # page.screenshot automatically overwrites if the file already exists
    page.screenshot(path=screenshot_path)
    logging.info(f"[{source_type}] {channel_name}: Saved debug screenshot to {screenshot_path}")
    
    return None

def update_playlist():
    final_playlist = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for channel in channels:
            name = channel["name"]
            logging.info(f"--- Processing {name} ---")
            
            # 1. Primary Attempt
            stream_url = extract_m3u8(page, channel["primary"], name, "PRIMARY")
            
            # 2. Fallback Attempt
            if not stream_url and channel.get("backup"):
                logging.info(f"[FALLBACK] Primary failed. Attempting backup for {name}...")
                stream_url = extract_m3u8(page, channel["backup"], name, "BACKUP")
                
            if stream_url:
                final_playlist[name] = stream_url
            else:
                logging.error(f"[FATAL] Both primary and backup sources failed for {name}.")

        browser.close()
        
    return final_playlist

def save_m3u(playlist_dict, filename="playlist.m3u"):
    """Writes the successful streams to standard IPTV format."""
    logging.info(f"Writing {len(playlist_dict)} working channels to {filename}...")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in playlist_dict.items():
            f.write(f"#EXTINF:-1, {name}\n{url}\n")
    logging.info("Playlist update complete.")

if __name__ == "__main__":
    working_streams = update_playlist()
    save_m3u(working_streams)
