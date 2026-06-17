from threads import threads_benchmark
from multiprocesses import multiprocess_benchmark
from asyncing import async_benchmark
from parsing.parse_data import parse_profs, generate_warriors
import sys

number = sys.argv[1]
threads_benchmark(10, int(number))
multiprocess_benchmark(int(number))
async_benchmark(int(number))


parse_profs()
