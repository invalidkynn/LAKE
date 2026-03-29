import time
import asyncio
import random
import string
import logging
import aiohttp
import requests
import os
from os import system
from typing import List

# --- CONFIGURATION ---
# Paste your webhook URL here to avoid typing it every time
WEBHOOK_URL = "WEBHOOK_URL_HERE" 
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(message)s')

def print_banner():
    system('cls||clear')
    print('''
 __         ______     __  __     ______    
/\ \       /\  __ \   /\ \/ /    /\  ___\   
\ \ \____  \ \  __ \  \ \  _"-.  \ \  __\   
 \ \_____\  \ \_\ \_\  \ \_\ \_\  \ \_____\ 
  \/_____/   \/_/\/_/   \/_/\/_/   \/_____/ 
                                            
                    LAKE - Made By JXYV
    ''')

def write_file(arg: str) -> None:
    with open('hits.txt', 'a', encoding='UTF-8') as f:
        f.write(f'{arg}\n')

def send_webhook(webhook_url, user):
    if not webhook_url or "YOUR_WEBHOOK" in webhook_url:
        return
    
    embed = {
        "username": "lake checker",
        "content": "user available!",
        "embeds": [{
            "title": f"**{user}**",
            "description": f"username **{user}** might be available!\n[Check Profile](https://www.tiktok.com/@{user})",
            "color": 0x00FF00
        }]
    }
    try:
        requests.post(webhook_url, json=embed)
    except Exception as e:
        logging.error(f"Webhook failed: {e}")

def generate_usernames(amount, length):
    pool = string.ascii_lowercase + string.digits
    return [''.join(random.choice(pool) for _ in range(length)) for _ in range(amount)]

def load_from_txt():
    filename = 'usernames.txt'
    if not os.path.exists(filename):
        logging.error(f"'{filename}' not found! Creating an empty one.")
        open(filename, 'w').close()
        return []
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

class Checker:
    def __init__(self, webhook_url: str, usernames: List[str], max_concurrent: int = 3):
        self.webhook_url = webhook_url
        self.to_check = usernames
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]

    async def _check(self, session: aiohttp.ClientSession, username: str) -> None:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(1.5, 3)) # Slightly slower to be safer
            
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
            }

            url = f'https://www.tiktok.com/@{username}'
            
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 404:
                        logging.info(f'[AVAILABLE] @{username}')
                        write_file(username)
                        send_webhook(self.webhook_url, username)
                    
                    elif response.status == 200:
                        content = await response.text()
                        if 'webapp-user-title' not in content and '"userInfo":' not in content:
                            logging.info(f'[AVAILABLE] @{username}')
                            write_file(username)
                            send_webhook(self.webhook_url, username)
                        else:
                            logging.info(f'[TAKEN] @{username}')

                    elif response.status == 429:
                        logging.warning(f'[RATE LIMIT] IP flagged. Cooling down...')
                        await asyncio.sleep(60)
                    
                    else:
                        logging.info(f'[STATUS {response.status}] @{username}')

            except Exception as e:
                logging.debug(f"Connection error for {username}: {e}")

    async def start(self):
        connector = aiohttp.TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self._check(session, u) for u in self.to_check]
            await asyncio.gather(*tasks)

if __name__ == '__main__':
    print_banner()
    
    print("[1] Generate Random Usernames")
    print("[2] Read from usernames.txt")
    choice = input("\nSelect Option: ")

    if choice == '1':
        letters = int(input("Number of letters: "))
        batch_size = 20 
        while True:
            username_list = generate_usernames(batch_size, letters)
            checker = Checker(WEBHOOK_URL, username_list, max_concurrent=3)
            asyncio.run(checker.start())
            logging.info("Batch complete. Resting...")
            time.sleep(15)
    else:
        username_list = load_from_txt()
        if not username_list:
            print("No usernames found in usernames.txt. Exiting.")
        else:
            checker = Checker(WEBHOOK_URL, username_list, max_concurrent=2)
            asyncio.run(checker.start())
            print("Finished checking list.")
