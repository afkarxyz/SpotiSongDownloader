import requests
import urllib.parse

def get_data(link):
    try:
        response = requests.get(
            'https://spotisongdownloader.to/api/composer/spotify/xsingle_track.php', 
            params={'url': link}
        )
        return response.json()
    
    except Exception as error:
        print(f'Error: {error}')
        return None

def get_url(track_info):
    url = 'https://spotisongdownloader.to/api/composer/spotify/wertyuht3456.php'
    
    payload = {
        'song_name': track_info['song_name'],
        'artist_name': track_info['artist'],
        'url': track_info['url']
    }
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Cookie': 'PHPSESSID=j1ckcp3uapkmdhs22htg11fqvf; _ga=GA1.1.15078990.1738683269; _ga_X67PVRK9F0=GS1.1.1738683268.1.1.1738683277.0.0.0; quality=m4a',
        'Origin': 'https://spotisongdownloader.to',
        'Referer': 'https://spotisongdownloader.to/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        download_data = response.json()
        
        encoded_link = urllib.parse.quote(download_data['dlink'], safe=':/?=')
        return encoded_link
    
    except requests.RequestException as e:
        print(f'Download error: {e}')
        return None
