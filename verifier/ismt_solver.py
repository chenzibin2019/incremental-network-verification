from z3 import Solver, And, Or, If, Int

class iSMTSolver(object):
    def __init__(self):
        self.solver = Solver()
        self.param_dependencies = {}

    def add(self, constraint):
        if constraint is None: return 
        self.solver.add(constraint)

    def addDependency(self, p, w):
        if p not in self.param_dependencies: self.param_dependencies[p] = []
        if w not in self.param_dependencies[p]: self.param_dependencies[p].append(w)
    
    def And(self, clist):
        if clist == []: return None
        return And(clist)

    def Or(self, clist):
        if clist == []: return None
        return Or(clist)

    def If(self, cond, a, b):
        return If(cond, a, b)

    def check(self):
        return self.solver.check()

    def model(self):
        return self.solver.model()