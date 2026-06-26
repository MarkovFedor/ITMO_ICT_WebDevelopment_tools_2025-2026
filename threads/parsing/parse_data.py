import asyncio
import threading
import queue
import time
import random
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import execute_values
import re
import ssl
from urllib.parse import urljoin

load_dotenv()

NUM_THREADS = 4
DELAY_BETWEEN_PAGES = 0.3
DELAY_BETWEEN_PROFESSIONS = 0.2

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def init_db():
    print(DB_CONFIG)
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_profession_title ON profession (title);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_name ON skill (name);")
    conn.commit()
    cur.close()
    conn.close()
    print("DB connection OK. Unique indexes ensured.")

async def fetch_page(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, timeout=20) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f"Error fetching {url}: status {resp.status}")
                return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

async def parse_catalog(catalog_url):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        html = await fetch_page(session, catalog_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    professions = []

    cards = soup.select('div.one_profession')
    if not cards:
        print("ERROR: No profession cards found. Check selector.")
        return []

    print(f"Found {len(cards)} profession cards.")

    for card in cards:
        title_tag = card.find('h2')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        desc_tag = card.select_one('div.bt.text p')
        description = desc_tag.get_text(strip=True) if desc_tag else ''

        skills = []
        prof_nav = card.find('div', class_='prof_nav')
        if prof_nav:
            for elem in prof_nav.select('div.help.nav'):
                skill_name = elem.get('data-title')
                if skill_name:
                    skills.append(skill_name.strip())

        professions.append((title, description, skills))
    return professions
    
async def populate_data(catalog):
    print("=== Parsing catalog page ===")
    data = await parse_catalog(catalog)
    if not data:
        print("No professions found. Check selectors.")
        return 0

    loop = asyncio.get_running_loop()
    def _insert():
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        for title, desc, skills in data:
            cur.execute(
                "INSERT INTO profession (title, description) VALUES (%s, %s) ON CONFLICT (title) DO NOTHING",
                (title, desc)
            )
            for sk in skills:
                cur.execute(
                    "INSERT INTO skill (name, description) VALUES (%s, '') ON CONFLICT (name) DO NOTHING",
                    (sk,)
                )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Saved {len(data)} professions and their skills.")
    await loop.run_in_executor(None, _insert)
    return len(data)

def generate_warrior(prof_ids, skill_ids):
    if not skill_ids:
        return None
    race = random.choice(["director", "worker", "junior"])
    name = f"Warrior_{random.randint(1000, 9999)}"
    level = random.randint(1, 20)
    prof_id = random.choice(prof_ids) if prof_ids else None
    num_skills = random.randint(1, min(4, len(skill_ids)))
    chosen_skills = random.sample(skill_ids, num_skills)
    return (race, name, level, prof_id), chosen_skills

def insert_warrior_batch(batch):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    for warrior_data, skill_ids in batch:
        cur.execute(
            "INSERT INTO warrior (race, name, level, profession_id) VALUES (%s, %s, %s, %s) RETURNING id",
            warrior_data
        )
        warrior_id = cur.fetchone()[0]
        if skill_ids:
            link_data = [(sid, warrior_id, random.randint(1, 5)) for sid in skill_ids]
            execute_values(cur,
                "INSERT INTO skillwarriorlink (skill_id, warrior_id, level) VALUES %s",
                link_data
            )
    conn.commit()
    cur.close()
    conn.close()

def worker_warriors(task_queue):
    while True:
        try:
            batch = task_queue.get_nowait()
        except queue.Empty:
            break
        insert_warrior_batch(batch)
        print(f"[Thread-{threading.current_thread().name}] inserted {len(batch)} warriors")
        task_queue.task_done()

def generate_and_insert_warriors(prof_ids, skill_ids, total_warriors, batch_size=50):
    q = queue.Queue()
    batch = []
    for _ in range(total_warriors):
        warrior = generate_warrior(prof_ids, skill_ids)
        if warrior is None:
            continue
        batch.append(warrior)
        if len(batch) >= batch_size:
            q.put(batch)
            batch = []
    if batch:
        q.put(batch)

    threads = []
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=worker_warriors, args=(q,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

async def parse_profs(catalog=None, generate_warriors_flag=False):
    if not catalog:
        catalog = "https://atlas100.ru/catalog/?otrasl=all&prof=all"
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, init_db)
    print(catalog)
    data_len = await populate_data(catalog)
    print(data_len)
    if not data_len:
        print("ERROR: No professions or skills found")
        return None
    return f'Найдено {data_len} профессий и навыков'

async def generate_warriors(count):
    loop = asyncio.get_running_loop()
    def _get_ids():
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT id FROM profession")
        prof_ids = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT id FROM skill")
        skill_ids = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return prof_ids, skill_ids

    prof_ids, skill_ids = await loop.run_in_executor(None, _get_ids)
    if not prof_ids:
        print("ERROR: No professions found.")
        return

    start = time.time()
    await loop.run_in_executor(None, generate_and_insert_warriors, prof_ids, skill_ids, count, 50)
    print(f"Generated in {time.time() - start:.2f} sec")

async def main():
    await parse_profs()
    await generate_warriors(200)

if __name__ == "__main__":
    asyncio.run(main())