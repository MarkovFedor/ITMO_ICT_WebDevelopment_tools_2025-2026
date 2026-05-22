import threading
import queue
import time
import psycopg2
import requests
from bs4 import BeautifulSoup
from datetime import datetime

DB_CONFIG = {
    'dbname': 'parsing_lab',
    'user': 'postgres',
    'password': 'pass',
    'host': 'localhost',
    'port': 5432
}
NUM_THREADS = 4

def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parsed_pages (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def parse_and_save(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else 'No title'
    except Exception as e:
        title = f'Error: {e}'

    # Каждый поток открывает своё соединение
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO parsed_pages (url, title, parsed_at) VALUES (%s, %s, %s)',
        (url, title, datetime.now())
    )
    conn.commit()
    cur.close()
    conn.close()
    print(f'[Thread-{threading.current_thread().name}] {url} -> {title[:50]}')

def worker(q):
    while True:
        try:
            url = q.get_nowait()
        except queue.Empty:
            break
        parse_and_save(url)
        q.task_done()

def main():
    init_db()
    urls = [
        'https://example.com',
        'https://httpbin.org/get',
        'https://www.python.org',
        'https://www.google.com',
    ] * 2  # 8 адресов

    start = time.time()
    q = queue.Queue()
    for url in urls:
        q.put(url)

    threads = []
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=worker, args=(q,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    elapsed = time.time() - start
    print(f'Общее время (threading): {elapsed:.2f} сек')

if __name__ == '__main__':
    main()