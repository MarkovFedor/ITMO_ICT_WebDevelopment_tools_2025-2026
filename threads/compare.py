from threads import threads_benchmark
from multiprocesses import multiprocess_benchmark
from asyncing import async_benchmark
import sys

number = sys.argv[1]
threads_benchmark(10, int(number))
multiprocess_benchmark(int(number))
async_benchmark(int(number))
