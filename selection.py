import sys
import random
import time
from z3 import * 

def test(a):
    solver = Solver()
    constraints_or = []
    for i in range(0, a):
        test = i #random.randint(100, 1000)
        solver.add(Int('r')<=test)
        constraints_or.append(Int('r')==test)

    solver.add(Or(constraints_or))

    t1 = time.time()
    assert solver.check() == sat
    t2 = time.time()

    return t2-t1

if __name__ == '__main__':
    kk=[100, 1000, 10000, 100000]
    for k in kk:
        print(k,test(k))
