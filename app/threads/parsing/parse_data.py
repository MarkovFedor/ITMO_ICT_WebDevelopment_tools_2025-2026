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
from db_operations import DB_CONFIG
load_dotenv()

NUM_THREADS = 4
WARRIORS_TO_GENERATE = 500
# Задержки между запросами (вежливость)
DELAY_BETWEEN_PAGES = 0.3
DELAY_BETWEEN_PROFESSIONS = 0.2
CATALOG_URL = "https://atlas100.ru/catalog/?otrasl=all&prof=all"

def init_db():
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

def parse_catalog():
    """Парсит страницу каталога и возвращает список (название, [навыки])."""
    html = fetch_page(CATALOG_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    professions = []

    # Ищем карточки профессий – обычно это div, li или section с классом, содержащим 'catalog', 'prof', 'item'
    # Перебираем наиболее вероятные контейнеры, пока не найдём ненулевое количество.
    cards = soup.select('div.catalog-item, div.prof-item, div.profession-card, li.catalog__item, section.catalog__item')
    if not cards:
        # Попробуем найти любые блоки, внутри которых есть ссылка на профессию и теги навыков
        cards = soup.select('[class*="catalog"] [class*="item"], [class*="prof"]')
    if not cards:
        print("ERROR: Could not find profession cards. Please check the HTML structure and update selectors.")
        return []

    print(f"Found {len(cards)} profession cards.")

    for card in cards:
        # Название профессии: обычно внутри тега h2, h3 или a с классом title/name
        title_tag = card.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name', re.I))
        if not title_tag:
            title_tag = card.find(['h2', 'h3', 'h4', 'a'])
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # Навыки: ищем список ul с навыками, либо отдельные span/tag
        skills = []
        # Ищем блок с навыками по классам (skill, skills, tags, competencies)
        skills_container = card.find(['ul', 'div'], class_=re.compile(r'skill|tag|competen', re.I))
        if skills_container:
            for li in skills_container.find_all('li'):
                sk = li.get_text(strip=True)
                if sk:
                    skills.append(sk)
        # Если не нашли списка, ищем теги-спаны
        if not skills:
            skill_tags = card.select('span.skill, span.tag, span.skill-tag, div.skill, div.tag')
            for tag in skill_tags:
                sk = tag.get_text(strip=True)
                if sk:
                    skills.append(sk)

        professions.append((title, skills))

    return professions

def populate_data():
    print("=== Parsing catalog page ===")
    data = parse_catalog()
    if not data:
        print("No professions found. Check selectors.")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for title, skills in data:
        # Вставляем профессию
        cur.execute(
            "INSERT INTO profession (title, description) VALUES (%s, '') ON CONFLICT (title) DO NOTHING",
            (title,)
        )
        # Вставляем навыки
        for sk in skills:
            cur.execute(
                "INSERT INTO skill (name, description) VALUES (%s, '') ON CONFLICT (name) DO NOTHING",
                (sk,)
            )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Saved {len(data)} professions and their skills.")

# ---------- Генерация воинов (без изменений) ----------
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

def main():
    init_db()
    populate_data()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT id FROM profession")
    prof_ids = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT id FROM skill")
    skill_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    if not prof_ids or not skill_ids:
        print("ERROR: No professions or skills found in DB. Cannot generate warriors.")
        return

    print(f"Generating {WARRIORS_TO_GENERATE} warriors...")
    start = time.time()
    generate_and_insert_warriors(prof_ids, skill_ids, WARRIORS_TO_GENERATE, batch_size=50)
    elapsed = time.time() - start
    print(f"Total time: {elapsed:.2f} sec")

if __name__ == '__main__':
    main()