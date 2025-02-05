import requests

def get_cookie():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        session = requests.Session()
        response = session.get('https://spotisongdownloader.to/', headers=headers)
        response.raise_for_status()
        cookies = session.cookies.get_dict()
        print(f"PHPSESSID={cookies['PHPSESSID']}; quality=m4a")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_cookie()