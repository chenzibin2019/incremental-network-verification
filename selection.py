import sys
import random
import time
from z3 import * 
import numba as nb


def test(a):
    solver = Solver()
    constraints_or = []
    for i in range(0, a):
        test = i #random.randint(100, 1000)
        constraints_or.append(Int('r')==test)


    #t1 = time.time()
    #assert solver.check() == sat
    #t2 = time.time()

@nb.jit()
def test1(a):
    constraints_or = []
    for i in range(0, a):
        test = i #random.randint(100, 1000)
        constraints_or.append(Int('r')==test)


if __name__ == '__main__':
    kk=[100, 1000, 10000, 100000]
    for k in kk:
        t1 = time.time()
        test(k)
        t2 = time.time()
        test1(k)
        t3 = time.time()
        print(t3-t2,t2-t1)
