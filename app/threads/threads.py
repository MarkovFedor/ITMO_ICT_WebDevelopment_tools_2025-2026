import threading
import time

def sync_counting(number):
    result = 0
    for i in range(1, number):
        result+=i
    print(result)

def cut(number, chunks):
    size = number//chunks
    remainder = number % chunks
    ranges = []
    start = 1
    for i in range(chunks):
        part_size = size + 1 if i < remainder else size
        end = start + part_size - 1
        ranges.append((start, end))
        start = end + 1

    return ranges

total = []
lock = threading.Lock()

def count_sum(low, high):
    result = 0
    for i in range(low, high+1):
        result += i
    with lock:
        total.append(result)

def multi_threading(max, chunks):
    now = time.perf_counter()
    threads = []
    results = cut(max, chunks)
    for i in range(chunks):
        thread = threading.Thread(target=count_sum, args=results[i])
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    after = time.perf_counter()
    print(f'{sum(total)} : {after - now}')


def threads_benchmark(chunks, max):
    print('Multithread result: ')
    multi_threading(max, chunks)

def single_thread_benchmark(max):
    now = time.perf_counter()
    print('Single thread result')
    result = sum(list(range(1,max+1)))
    after = time.perf_counter()
    print(f'{result}: {after-now:.8f}')
