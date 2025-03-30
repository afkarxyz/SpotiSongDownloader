import requests
import urllib.parse
import re

def get_cookie():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    }

    try:
        session = requests.Session()
        response = session.get('https://spotisongdownloader.to/', headers=headers)
        response.raise_for_status()
        cookies = session.cookies.get_dict()
        return f"PHPSESSID={cookies['PHPSESSID']}; quality=m4a"
        
    except requests.exceptions.RequestException:
        return None

def get_api():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get('https://spotisongdownloader.to/track.php', headers=headers)
        response.raise_for_status()
        
        match = re.search(r'url:\s*"(/api/composer/spotify/[^"]+)"', response.text)
        if match:
            api_endpoint = match.group(1)
            return f"https://spotisongdownloader.to{api_endpoint}"
        
    except requests.exceptions.RequestException:
        return None

def get_data(link):
    try:
        response = requests.get(
            'https://spotisongdownloader.to/api/composer/spotify/xsingle_track.php', 
            params={'url': link}
        )
        return response.json()
    
    except:
        return None

def get_url(track_data, cookie):
    url = get_api()
    
    payload = {
        'song_name': track_data['song_name'],
        'artist_name': track_data['artist'],
        'url': track_data['url']
    }
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Cookie': cookie,
        'Origin': 'https://spotisongdownloader.to',
        'Referer': 'https://spotisongdownloader.to/track.php',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        download_data = response.json()
        
        encoded_link = urllib.parse.quote(download_data['dlink'], safe=':/?=')
        return encoded_link
    
    except:
        return None

def main():
    url = "https://open.spotify.com/track/4wJ5Qq0jBN4ajy7ouZIV1c"
    
    cookie = get_cookie()
    if not cookie:
        return
    
    track_data = get_data(url)
    if not track_data:
        return
        
    link = get_url(track_data, cookie)
    if link:
        print(link)

if __name__ == "__main__":
    main()
