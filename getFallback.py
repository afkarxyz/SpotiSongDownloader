import requests
from mutagen.mp4 import MP4, MP4Cover

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

def get_track_data(spotify_url, cookie):
    api_url = "https://spotisongdownloader.to/api/composer/spotify/xsingle_track.php"
    headers = {'Cookie': cookie}
    try:
        response = requests.get(api_url, params={'url': spotify_url}, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

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

def convert_link(download_data, cookie):
    convert_url = "https://spotisongdownloader.to/api/convertRapidAPI.php"
    params = {'url': download_data['link']}
    headers = {'Cookie': cookie}
    try:
        response = requests.post(convert_url, data=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def save_track(url, filename):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return filename
    except requests.exceptions.RequestException:
        return None

def embed_metadata(file_path, track_data):
    audio = MP4(file_path)
    audio["©nam"] = track_data['song_name']
    audio["©ART"] = track_data['artist']
    audio["©alb"] = track_data['album_name']
    audio["©day"] = track_data['released']
    
    try:
        img_response = requests.get(track_data['img'])
        img_response.raise_for_status()
        audio["covr"] = [MP4Cover(img_response.content, MP4Cover.FORMAT_JPEG)]
    except requests.exceptions.RequestException:
        pass
    
    audio.save()

def main():
    spotify_url = "https://open.spotify.com/track/2plbrEY59IikOBgBGLjaoe"
    cookie = get_cookie()
    if not cookie:
        print("Failed to get cookie.")
        return
    
    track_data = get_track_data(spotify_url, cookie)
    if track_data:
        print("Track Data:")
        print(track_data)
        
        yt_data = search_track(track_data, cookie)
        if yt_data:
            print("YouTube Search Data:")
            print(yt_data)
            
            download_data = get_link(track_data, yt_data, cookie)
            if download_data:
                print("Download Link:")
                print(download_data)
                
                converted_data = convert_link(download_data, cookie)
                if converted_data:
                    print("Converted File:")
                    print(converted_data)
                    
                    file_path = save_track(converted_data['dlink'], "downloaded_song.m4a")
                    if file_path:
                        embed_metadata(file_path, track_data)
                        print("Metadata successfully embedded.")
                    else:
                        print("Failed to download file.")
                else:
                    print("Failed to convert file.")
            else:
                print("Failed to get download link.")
        else:
            print("Failed to retrieve YouTube search data.")
    else:
        print("Failed to retrieve track data.")

if __name__ == "__main__":
    main()