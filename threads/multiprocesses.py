import multiprocessing
import time

cores = multiprocessing.cpu_count()
optimal = max(1, cores-1)

print(f'{optimal}')

def count_big_number(low=1, high=10000):
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

def multiprocess_counting(number, optimal):
    ranges = cut(number, optimal)
    shared_result = multiprocessing.Value('i', 0)
    with multiprocessing.Pool(processes=optimal) as pool:
        partial_sums = pool.starmap(count_big_number, ranges)
    return sum(partial_sums)



def multiprocess_benchmark(num):
    print('Multiprocess counting result')
    now = time.perf_counter()
    result = multiprocess_counting(num, optimal)
    after = time.perf_counter()
    print(f'{result} : {after - now}')