import requests
import re
import urllib.parse
import json

class SpotiSongDownloader:
    def __init__(self):
        self.cookies = {
            "PHPSESSID": "0be4464e182566c83c0b55a304c8f776",
            "ttpassed": "ttpassed",
            "cf_token": "0eca9b019bb42ba9a4a99124c6dc114c",
            "quality": "m4a"
        }
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        self.api_url = None
        self.base_url = "https://spotisongdownloader.to/"

    def get_headers(self, referer=None, with_cookies=False, is_post=False):
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": self.user_agent,
            "referer": referer or self.base_url,
            "x-requested-with": "XMLHttpRequest"
        }
        
        if with_cookies:
            headers["cookie"] = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
            
        if is_post:
            headers.update({
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "origin": self.base_url.rstrip('/')
            })
            
        return headers

    def find_api_url(self):
        if not self.api_url:
            try:
                url = f"{self.base_url}track.php"
                res = requests.get(url, headers=self.get_headers())
                match = re.search(r'url:\s*"(\/api\/composer\/spotify\/[^"]+)"', res.text)
                if match and match.group(1):
                    self.api_url = f"{self.base_url}{match.group(1).lstrip('/')}"
            except Exception:
                pass
                
        return bool(self.api_url)

    def clean_text(self, text):
        if text is None:
            return ""
        return re.sub(r'[^\w\s-]', '', text.replace('&amp;', '&')).strip()

    def get_track_info(self, url):
        api_url = f"{self.base_url}api/composer/spotify/xsingle_track.php"
        res = requests.get(
            api_url, 
            headers=self.get_headers(f"{self.base_url}track.php", with_cookies=True), 
            params={"url": url}
        )

        try:
            data = res.json()
            if data.get('res') != 200:
                return None

            return {
                "song_name": self.clean_text(data.get('song_name')),
                "artist": self.clean_text(data.get('artist')),
                "img": data.get('img'),
                "duration": data.get('duration'),
                "url": data.get('url'),
                "released": data.get('released'),
                "album_name": data.get('album_name')
            }
        except Exception:
            return None

    def get_download_link(self, track_info):
        if not track_info or not track_info.get('song_name') or not track_info.get('artist') or not self.api_url:
            return None
        
        form_data = {
            "song_name": track_info.get('song_name'),
            "artist_name": track_info.get('artist'),
            "url": track_info.get('url', "")
        }
        
        form = urllib.parse.urlencode(form_data)

        res = requests.post(
            self.api_url, 
            data=form, 
            headers=self.get_headers(f"{self.base_url}track.php", with_cookies=True, is_post=True)
        )

        try:
            data = res.json()
            if data.get('status') == "success" and data.get('dlink'):
                return {"dlink": data.get('dlink').replace('\/', '/')}
            return data
        except Exception:
            return None

    def get_download_info(self, url):
        self.api_url = None
        
        if not self.find_api_url():
            return {"error": "Failed to find API URL"}

        track_info = self.get_track_info(url)
        if not track_info:
            return {"error": "Track not found"}

        download_data = self.get_download_link(track_info)
        if not download_data:
            return {"error": "Failed to fetch download link"}

        if download_data.get('dlink'):
            return {**track_info, "dlink": download_data.get('dlink')}
        else:
            return {**track_info, "error": "Download link not available"}


def main():
    track_id = "7so0lgd0zP2Sbgs2d7a1SZ"
    spotify_url = f"https://open.spotify.com/track/{track_id}"
    
    spotify = SpotiSongDownloader()
    result = spotify.get_download_info(spotify_url)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()