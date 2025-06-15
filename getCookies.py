import asyncio
import zendriver as zd
import random

async def get_cookies():
    url = "https://open.spotify.com/track/7so0lgd0zP2Sbgs2d7a1SZ"
    headless = False
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            browser = await zd.start(headless=headless)
            page = await browser.get("https://spotisongdownloader.to")
            
            await page.wait_for("#id_url")

            await page.evaluate(f"""
                document.querySelector("#id_url").value = "{url}";
                document.querySelector("#id_url").dispatchEvent(new Event('input', {{ bubbles: true }}));
            """)            
            generate_link_button = await page.wait_for('#submit')
            
            if generate_link_button:
                await page.evaluate("""
                    document.querySelector('#submit').click()
                """)
                
                await asyncio.sleep(2)
                
                cookies_list = await browser.cookies.get_all()
                
                await browser.stop()
                cookies_dict = {}
                for cookie in cookies_list:
                    if cookie.name in ["PHPSESSID", "quality", "_ga", "_ga_X67PVRK9F0"]:
                        cookies_dict[cookie.name] = cookie.value
                
                if "quality" not in cookies_dict:
                    cookies_dict["quality"] = "m4a"
                    
                return cookies_dict
            else:
                await browser.stop()
                
        except Exception as e:
            try:
                if 'browser' in locals() and browser:
                    await browser.stop()
            except:
                pass
        
        retry_count += 1
        await asyncio.sleep(random.uniform(1, 3))
    
    return {"error": f"Failed after {max_retries} attempts"}

async def main():
    result = await get_cookies()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())