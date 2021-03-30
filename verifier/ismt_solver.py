from z3 import Solver, And, Or, If, Int

class iSMTSolver(object):
    def __init__(self, verbose=False):
        self.solver = Solver()
        self.param_dependencies = {}
        self.param_constraints = []
        self.params = {}
        self.constraint_prep = []
        self.verbose = verbose

    def add(self, constraint):
        if self.verbose: print('add', constraint)
        self.solver.add(constraint)

    def addDependency(self, p, w):
        if p not in self.param_dependencies: self.param_dependencies[p] = []
        if w not in self.param_dependencies[p]: self.param_dependencies[p].append(w)

    def addParameter(self, p, v, verbose=False):
        if p not in self.params:
            self.params[p] = v
            if verbose: print('add parameter', p, '=', v)
            self.param_constraints.append(p == v)
        elif verbose: 
            print('dup', p)

    def rebuiltParamConstraints(self, k=None, v=None):
        self.param_constraints = []
        for p in self.params:
            if p.__str__() == k: self.param_constraints.append(p == v)
            else: self.param_constraints.append(p == self.params[p])

    def check(self):
        self.solver.push()
        if self.param_constraints != []: self.add(And(self.param_constraints))
        return self.solver.check()

    def reset(self):
        self.solver = Solver()
        self.param_dependencies = {}
        self.param_constraints = []
        self.params = {}
        return self
    
    def clear(self):
        self.solver = Solver()
        return

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