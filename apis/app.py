from flask import Flask, jsonify
import requests
import urllib.parse
import re

app = Flask(__name__)

def get_cookie(use_m4a=False):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    }
    try:
        session = requests.Session()
        response = session.get('https://spotisongdownloader.to/', headers=headers)
        response.raise_for_status()
        cookies = session.cookies.get_dict()
        if use_m4a:
            return f"PHPSESSID={cookies['PHPSESSID']}; quality=m4a"
        else:
            return f"PHPSESSID={cookies['PHPSESSID']}"
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

# Primary
def get_track_data(track_id):
    spotify_url = f"https://open.spotify.com/track/{track_id}"
    cookie = get_cookie()
    if not cookie:
        return None, None, None
    
    try:
        response = requests.get(
            'https://spotisongdownloader.to/api/composer/spotify/xsingle_track.php', 
            params={'url': spotify_url},
            headers={'Cookie': cookie}
        )
        response.raise_for_status()
        track_data = response.json()
        metadata = {
            'song_name': track_data.get('song_name', ''),
            'artist': track_data.get('artist', ''),
            'img': track_data.get('img', ''),
            'released': track_data.get('released', ''),
            'album_name': track_data.get('album_name', '')
        }
        m4a_cookie = get_cookie(use_m4a=True)
        return track_data, metadata, m4a_cookie
    except requests.exceptions.RequestException:
        return None, None, None

# Fallback
def search_track(track_data, cookie):
    ytsearch_url = "https://spotisongdownloader.to/api/composer/ytsearch/mytsearch.php"
    params = {
        'name': track_data['song_name'],
        'artist': track_data['artist'],
        'album': track_data['album_name'],
        'link': track_data['url']
    }
    headers = {'Cookie': cookie}
    try:
        response = requests.get(ytsearch_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

# Primary
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

# Fallback
def get_link(track_data, yt_data, cookie):
    rapidmp3_url = "https://spotisongdownloader.to/api/rapidmp3.php"
    params = {
        'q': yt_data['videoid'],
        'url': track_data['url'],
        'name': track_data['song_name'],
        'artist': track_data['artist'],
        'album': track_data['album_name']
    }
    headers = {'Cookie': cookie}
    try:
        response = requests.get(rapidmp3_url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

@app.route('/<track_id>')
def download_track(track_id):
    track_data, metadata, m4a_cookie = get_track_data(track_id)
    if not track_data:
        return jsonify({"error": "Failed to get track data"}), 404
        
    download_link = get_url(track_data, m4a_cookie)
    source = "primary"
    
    if not download_link:
        source = "fallback"
        standard_cookie = get_cookie(use_m4a=False)
        if not standard_cookie:
            return jsonify({"error": "Failed to get cookie"}), 500
            
        yt_data = search_track(track_data, standard_cookie)
        if not yt_data:
            return jsonify({"error": "Failed to find matching YouTube data"}), 500
            
        download_data = get_link(track_data, yt_data, standard_cookie)
        if not download_data:
            return jsonify({"error": "Failed to get download link"}), 500
            
        download_link = download_data['link']
    
    return jsonify({
        "url": download_link,
        "metadata": metadata,
        "source": source
    })

if __name__ == "__main__":
    app.run(debug=True)
