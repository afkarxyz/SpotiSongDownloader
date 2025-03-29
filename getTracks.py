import requests
import re

BASE_URL = "https://spotisongdownloader.to"
DEFAULT_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
}

def create_session():
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    return session

def get_cookie(url=BASE_URL):
    try:
        session = create_session()
        session.get(url)
        return "; ".join([f"{c.name}={c.value}" for c in session.cookies])
    except Exception as error:
        print(f"Error getting cookies: {str(error)}")
        return ""

def clean(text):
    return re.sub(r'[^\w\s-]', '', text.replace('&amp;', '&')).strip()

def get_api():
    try:
        session = create_session()
        response = session.get(f"{BASE_URL}/track.php")
        match = re.search(r'url:\s*"(\/api\/composer\/spotify\/[^"]+)"', response.text)
        return f"{BASE_URL}{match.group(1)}" if match else None
    except Exception as error:
        print(f"Error finding API URL: {str(error)}")
        return None

def get_data(url):
    try:
        session = create_session()
        cookies = get_cookie(BASE_URL)
        response = session.get(
            f"{BASE_URL}/api/composer/spotify/xsingle_track.php",
            params={"url": url},
            headers={
                "cookie": cookies,
                "referer": BASE_URL
            }
        )
        
        data = response.json()
        if data.get("res") != 200:
            return None
        
        data["song_name"] = clean(data["song_name"])
        data["artist"] = clean(data["artist"])
        return data
    except Exception as error:
        print(f"Error fetching track info: {str(error)}")
        return None

def get_url(track_info, cookies=None):
    try:
        session = create_session()
        
        if not track_info or not track_info.get("song_name") or not track_info.get("artist"):
            return None
        
        api_url = get_api()
        if not api_url:
            return {"error": "Failed to detect API URL"}
        
        if not cookies:
            cookies = get_cookie(f"{BASE_URL}/track.php")
            
        form_data = {
            "song_name": track_info["song_name"],
            "artist_name": track_info["artist"],
            "url": track_info.get("url", "")
        }
        
        response = session.post(
            api_url,
            data=form_data,
            headers={
                "cookie": cookies,
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "origin": BASE_URL,
                "referer": f"{BASE_URL}/track.php"
            }
        )
        
        result = response.json()
        if result and "dlink" in result:
            return result["dlink"]
        return None
    except Exception as error:
        print(f"Error fetching download link: {str(error)}")
        return None