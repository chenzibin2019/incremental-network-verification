from z3 import Solver, And, Or, If, Int

class iSMTSolver(object):
    def __init__(self):
        self.solver = Solver()
        self.param_dependencies = {}
        self.param_constraints = []
        self.params = {}

    def add(self, constraint):
        if constraint is None: return 
        self.solver.add(constraint)

    def addDependency(self, p, w):
        if p not in self.param_dependencies: self.param_dependencies[p] = []
        if w not in self.param_dependencies[p]: self.param_dependencies[p].append(w)

    def addParameter(self, p, v):
        if p not in self.params:
            self.params[p] = v
            self.param_constraints.append(p == v)

    def rebuiltParamConstraints(self, k, v):
        self.param_constraints = []
        for p in self.params:
            if p.__str__() == k: self.param_constraints.append(p == v)
            else: self.param_constraints.append(p == self.params[p])

    def check(self):
        self.solver.push()
        self.add(And(self.param_constraints))
        return self.solver.check()

    def And(self, clist):
        if clist == []: return None
        return And(clist)

    def Or(self, clist):
        if clist == []: return None
        return Or(clist)

    def If(self, cond, a, b):
        return If(cond, a, b)

    def model(self):
        return self.solver.model()