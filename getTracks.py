import requests
import urllib.parse

def get_data(link):
    try:
        response = requests.get(
            'https://spotisongdownloader.to/api/composer/spotify/xsingle_track.php', 
            params={'url': link}
        )
        data = response.json()
        
        return {
            'song_name': data['song_name'],
            'artist_name': data['artist'],
            'url': data['url']
        }
    
    except Exception as error:
        print(f'Error getting track data: {error}')
        return None

def get_url(track_data):
    url = 'https://spotisongdownloader.to/api/composer/spotify/wertyuht3456.php'
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Cookie': 'PHPSESSID=7uf4vrc1auogmgab4d6g6su1eg; quality=m4a',
        'Origin': 'https://spotisongdownloader.to',
        'Referer': 'https://spotisongdownloader.to/track.php',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36'
    }

    try:
        response = requests.post(url, data=track_data, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        if response_data.get('status') == 'success' and 'dlink' in response_data:
            download_link = response_data['dlink']
            return urllib.parse.quote(download_link, safe=':/?=')
        else:
            print("Error: Invalid response or status failed.")
            return None
            
    except requests.RequestException as e:
        print(f"Error getting download URL: {e}")
        return None

def process_track(spotify_url):
    track_data = get_data(spotify_url)
    if not track_data:
        return None
        
    download_url = get_url(track_data)
    return download_url

# spotify_url = 'https://open.spotify.com/track/4xigPf2sigSPmuFH3qCelB'
# result = process_track(spotify_url)
# print(result)
