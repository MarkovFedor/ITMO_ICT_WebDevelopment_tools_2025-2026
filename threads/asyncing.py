import asyncio
import time

async def count_big_number(low=1, high=10000):
    result = 0
    for i in range(low, high+1):
        result += i
    return result

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

async def count():
    number = 10000000
    chunks = 10
    tasks = []
    ranges = cut(number, chunks)
    now = time.perf_counter()
    for i in range(chunks):
        tasks.append(count_big_number(ranges[i][0], ranges[i][1]))
    results = await asyncio.gather(*tasks)
    total = sum(results)
    after = time.perf_counter()

    print(f'{total} : {after - now}')

asyncio.run(count())