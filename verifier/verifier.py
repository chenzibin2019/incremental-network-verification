from verifier.ismt_solver import iSMTSolver

class Verifier(object):
    def __init__(self, topo, args, loader=None):
        self.topo = topo
        self.solver = iSMTSolver()
        if loader is not None:
            getattr(topo, loader)(args)
