from flask import Flask, jsonify
import requests
import urllib.parse
import re

app = Flask(__name__)

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

def get_data(track_id):
    link = f"https://open.spotify.com/track/{track_id}"
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
    if not url:
        return None
    
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

@app.route('/<track_id>')
def download_track(track_id):
    cookie = get_cookie()
    if not cookie:
        return jsonify({"error": "Failed to get session cookie"}), 500
    
    track_data = get_data(track_id)
    if not track_data:
        return jsonify({"error": "Failed to get track data"}), 404
        
    download_link = get_url(track_data, cookie)
    if not download_link:
        return jsonify({"error": "Failed to get download URL"}), 500
    
    return jsonify({"url": download_link})

if __name__ == "__main__":
    app.run(debug=True)
