import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Define your channels with their primary (MarTV) and backup URLs.
# Note: Update the primary URLs if your exact MarTV paths differ slightly.
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
    """Navigates to the URL, clicks the player, and intercepts the .m3u8 request."""
    # Instantly return if the link is already a direct raw stream (like AdjaraTV backup)
    if url.endswith(".m3u8"):
        return url

    print(f"  [{source_type}] Loading {url}...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        
        with page.expect_response(lambda response: ".m3u8" in response.url, timeout=15000) as response_info:
            
            # Dynamic locator captures MarTV, Arxebi, and Televizia players
            player = page.locator("iframe, video, .video-js, .player-container").first
            
            if player.is_visible(timeout=5000):
                box = player.bounding_box()
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            else:
                print("    -> Player not visible. Stream may not initialize.")
                
        return response_info.value.url

    except PlaywrightTimeoutError:
        print("    -> Timeout: No stream manifest requested.")
        return None
    except Exception as e:
        print(f"    -> Error: {e}")
        return None

def update_playlist():
    final_playlist = {}
    
    with sync_playwright() as p:
        # Run headless once you verify it works smoothly
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for channel in channels:
            name = channel["name"]
            print(f"\nProcessing {name}...")
            
            # 1. Try Primary Link (MarTV)
            stream_url = extract_m3u8(page, channel["primary"], name, "PRIMARY")
            
            # 2. Try Backup Link if Primary fails
            if not stream_url and channel.get("backup"):
                print(f"  [FALLBACK] Primary failed. Attempting backup for {name}...")
                stream_url = extract_m3u8(page, channel["backup"], name, "BACKUP")
                
            if stream_url:
                final_playlist[name] = stream_url
                print(f"  [SUCCESS] {name} captured successfully.")
            else:
                print(f"  [FAILED] Both primary and backup failed for {name}.")

        browser.close()
        
    return final_playlist

def save_m3u(playlist_dict, filename="playlist.m3u"):
    """Writes the successful streams to standard IPTV format."""
    print(f"\nWriting {len(playlist_dict)} channels to {filename}...")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in playlist_dict.items():
            f.write(f"#EXTINF:-1, {name}\n{url}\n")
    print("Update complete.")

if __name__ == "__main__":
    working_streams = update_playlist()
    save_m3u(working_streams)
