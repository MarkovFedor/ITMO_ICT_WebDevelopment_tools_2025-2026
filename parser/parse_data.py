import threading
import queue
import time
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2.extras import execute_values
import re
from urllib.parse import urljoin
load_dotenv()

NUM_THREADS = 4
#WARRIORS_TO_GENERATE = 500
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
    """Проверяем подключение и создаём уникальные индексы, если их нет."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_profession_title ON profession (title);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_skill_name ON skill (name);")
    conn.commit()
    cur.close()
    conn.close()
    print("DB connection OK. Unique indexes ensured.")

def fetch_page(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        return resp.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_catalog(catalog_url):
    """Парсит главную страницу каталога и возвращает список (название, описание, [навыки])"""
    html = fetch_page(catalog_url)
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
        # Название
        title_tag = card.find('h2')
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # Описание
        desc_tag = card.select_one('div.bt.text p')
        description = desc_tag.get_text(strip=True) if desc_tag else ''

        # Навыки
        skills = []
        prof_nav = card.find('div', class_='prof_nav')
        if prof_nav:
            skill_elems = prof_nav.select('div.help.nav')
            for elem in skill_elems:
                skill_name = elem.get('data-title')
                if skill_name:
                    skills.append(skill_name.strip())

        professions.append((title, description, skills))
        print(skills)
    return professions

def populate_data(catalog):
    print("=== Parsing catalog page ===")
    data = parse_catalog(catalog)
    if not data:
        print("No professions found. Check selectors.")
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for title, desc, skills in data:  # ← было (title, skills) → ошибка
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

def parse_profs(catalog,generate_warriors=False):
    if not catalog:
        catalog = "https://atlas100.ru/catalog/?otrasl=all&prof=all"
    init_db()
    print(catalog)
    data_len = populate_data(catalog)
    print(data_len)
    
    if not data_len:
        print("ERROR: No professions or skills found")
        return

    return f'Найдено len(data) профессий и навыков'

def generate_warriors(count):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id FROM profession")
    prof_ids = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM skill")
    skill_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    start = time.time()
    generate_and_insert_warriors(prof_ids, skill_ids, count, batch_size=50)