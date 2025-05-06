import nodriver as uc
import asyncio

async def get_cookies(sleep_time=3):
    browser = await uc.start()
    await browser.get('https://spotisongdownloader.to/')
    await asyncio.sleep(sleep_time)
    cookies_list = await browser.cookies.get_all()
    
    cookies = {}
    for cookie in cookies_list:
        if cookie.name in ["PHPSESSID", "cf_token", "ttpassed", "quality"]:
            cookies[cookie.name] = cookie.value
    
    browser.stop()
    return cookies

async def main():
    cookies = await get_cookies()
    for name, value in cookies.items():
        if name in ["PHPSESSID", "cf_token"]:
            print(f"{name}: {value}")

if __name__ == '__main__':
    uc.loop().run_until_complete(main())