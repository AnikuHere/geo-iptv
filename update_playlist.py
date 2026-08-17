import re
import urllib.request
import ssl

IPTV_ORG_URL = "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ge.m3u"
MY_M3U_FILE = "georgia_channels.m3u"

# Bypass SSL errors on cloud runners
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def fetch_setanta_block():
    try:
        req = urllib.request.Request(
            IPTV_ORG_URL, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            content = resp.read().decode('utf-8')
        
        # Match Setanta Sports 3 block from IPTV-ORG (handles optional EXTVLCOPT line)
        pattern = r'(#EXTINF:-1 tvg-id="SetantaSports3\.ge@SD"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+)'
        match = re.search(pattern, content)
        if match:
            # Rebrand tvg-id to setanta3 to match georgia_channels.m3u
            block = match.group(1).strip()
            return block.replace('tvg-id="SetantaSports3.ge@SD"', 'tvg-id="setanta3"')
        return None
    except Exception as e:
        print(f"Failed to fetch Setanta from IPTV-ORG: {e}")
        return None

def generate_gds_link():
    page_url = "https://tv.mar.tv/13"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://tv.mar.tv/"
    }
    
    try:
        req = urllib.request.Request(page_url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            html = resp.read().decode('utf-8')
        
        # 1. Search for direct index.m3u8 stream URL
        pattern = r'https?://[a-zA-Z0-9\.-]+\.mar\.tv/[a-f0-9]{32,64}/13[a-zA-Z0-9]*/index\.m3u8'
        match = re.search(pattern, html)
        if match:
            return match.group(0)
        
        # 2. Fallback: Search for 64-char dynamic token
        token_match = re.search(r'([a-f0-9]{64})', html)
        if token_match:
            return f"https://live1.mar.tv/{token_match.group(1)}/13sd/index.m3u8"
    except Exception as e:
        print(f"Failed to extract GDS link: {e}")
        
    return None

def update_my_playlist():
    setanta_block = fetch_setanta_block()
    new_gds_url = generate_gds_link()

    with open(MY_M3U_FILE, 'r', encoding='utf-8') as f:
        my_content = f.read()

    # Update Setanta Sports 3 entry
    if setanta_block:
        existing_setanta = r'#EXTINF:-1 tvg-id="(?:setanta3|SetantaSports3\.ge@SD)"[^\n]*\n(?:#EXTVLCOPT:[^\n]*\n)?[^\n]+'
        if re.search(existing_setanta, my_content):
            my_content = re.sub(existing_setanta, setanta_block, my_content)
            print("Setanta Sports 3 updated successfully.")
        else:
            print("Setanta pattern not found in local file.")

    # Update GDS TV entry
    if new_gds_url:
        gds_pattern = r'(#EXTINF:-1 tvg-id="gds"[^\n]*\n)[^\n]+'
        if re.search(gds_pattern, my_content):
            my_content = re.sub(gds_pattern, r'\g<1>' + new_gds_url, my_content)
            print(f"GDS TV updated: {new_gds_url}")
        else:
            print("GDS pattern not found in local file.")

    with open(MY_M3U_FILE, 'w', encoding='utf-8') as f:
        f.write(my_content)

if __name__ == "__main__":
    update_my_playlist()
