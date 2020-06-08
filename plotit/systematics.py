from __future__ import absolute_import, print_function
"""
Systematics classes (based on plotIt)
"""
__all__ = ("SystVar", "SystVarsForHist", "ParameterizedSystVar", "ConstantSystVar", "LogNormalSystVar", "ShapeSystVar")

from itertools import chain
from . import logger

from .plotit import lazyload

class SystVar(object):
    """ interface & base for a systematic variation (without specified histogram) """
    @staticmethod
    def default_filter(fName, fObj):
        """ returns True for any file name and pointer """
        return True
    def __init__(self, name, pretty_name=None, on=None):
        """ Constructor

        Arguments:
          name          systematic name (used internally and in names)
          pretty_name   pretty name (used in places where formatting is possible)
          on            a callable that takes a file name and argument, and returns
                        True if the systematic should be evaluated for that sample
        """
        self.name = name
        self.pretty_name = pretty_name if pretty_name is not None else name
        self.on = on if on is not None else SystVar.default_filter
        super(SystVar, self).__init__()
    def _repr_args(self):
        return (self.name,)
    def _repr_kwargs(self):
        return tuple((["pretty_name"] if self.pretty_name != self.name else [])+(["on"] if self.on != SystVar.default_filter else []))
    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, ", ".join(chain((repr(a) for a in self._repr_args()), ("{0}={1!r}".format(k,getattr(self, k)) for k in self._repr_kwargs()))))

    def forHist(self, hist):
        """ get variation for hist """
        return self.__class__.ForHist(hist, self)

    class ForHist(object):
        """ Interface & base for systematic variation for a single histogram """
        __slots__ = ("hist", "systVar")
        def __init__(self, hist, systVar):
            self.hist = hist
            self.systVar = systVar
        @property
        def nom(self):
            """ Nominal values """
            return self.hist.contents
        @property
        def up(self):
            """ Up variation values """
            return self.hist.contents
        @property
        def down(self):
            """ Down variation values """
            return self.hist.contents

try: ## python3 (avoid warning)
    from collections.abc import Mapping
except ImportError: ## python2
    from collections import Mapping
class SystVarsForHist(Mapping):
    """ dict-like object to assign as systVars to an entry

    (parent is the actual dictionary with SystVars) """
    __slots__ = ("hist", "parent", "_cached")
    def __init__(self, hist, parent):
        self.hist = hist
        self.parent = parent
        self._cached = dict()
    def __getitem__(self, ky):
        if ky in self._cached:
            return self._cached[ky]
        else:
            fp = self.parent[ky].forHist(self.hist)
            if isinstance(fp, ShapeSystVar.ForHist):
                self._cached[ky] = fp
            return fp
    def __iter__(self):
        for systVar in self.parent:
            yield systVar
    def __len__(self):
        return len(self.parent)

class ParameterizedSystVar(SystVar):
    """ base for constant etc. """
    def __init__(self, name, pretty_name=None, on=SystVar.default_filter):
        super(ParameterizedSystVar, self).__init__(name, pretty_name=pretty_name, on=on)
    def nom(self, hist):
        return hist.contents
    def up(self, hist):
        pass
    def down(self, hist):
        pass

    class ForHist(SystVar.ForHist):
        """ delegate everything to the corresponding systVar methods """
        __slots__ = tuple()
        def __init__(self, hist, systVar):
            super(ParameterizedSystVar.ForHist, self).__init__(hist, systVar)
        @property
        def nom(self):
            return self.systVar.nom(self.hist)
        @property
        def up(self):
            return self.systVar.up(self.hist)
        @property
        def down(self):
            return self.systVar.down(self.hist)

class ConstantSystVar(ParameterizedSystVar):
    """ constant scale up/down (given as the relative up variation, e.g. 1.2 for 20%) """
    def __init__(self, name, value, pretty_name=None, on=SystVar.default_filter):
        self.value = value
        super(ConstantSystVar, self).__init__(name, pretty_name=pretty_name, on=on)
    def _repr_args(self):
        return (self.name, self.value)

    def up(self, hist):
        return hist.contents*self.value
    def down(self, hist):
        return hist.contents*(2-self.value)

class LogNormalSystVar(ParameterizedSystVar):
    """ """
    def __init__(self, name, prior, postfit=0., postfit_error=None, postfit_error_up=None, postfit_error_down=None, pretty_name=None, on=SystVar.default_filter):
        if postfit_error_up is None:
            if postfit_error is not None:
                postfit_error_up = postfit_error
            else:
                postfit_error_up = 1.
        if postfit_error_down is None:
            if postfit_error is not None:
                postfit_error_down = postfit_error
            else:
                postfit_error_down = 1.
        # eval
        import math
        self.value = math.exp(postfit*math.log(prior))
        self.value_up = math.exp((postfit+postfit_error_up)*math.log(prior))
        self.value_down = math.exp((postfit-postfit_error_down)*math.log(prior))
        super(LogNormalSystVar, self).__init__(name, pretty_name=pretty_name, on=on)
    ## TODO __repr__

    def up(self, hist):
        return hist.contents*self.value_up
    def down(self, hist):
        return hist.contents*self.value_down

class ShapeSystVar(SystVar):
    """ for shapes """
    def __init__(self, name, pretty_name=None, on=SystVar.default_filter):
        self.name = name
        super(ShapeSystVar, self).__init__(name, pretty_name=pretty_name, on=on)

    class ForHist(SystVar.ForHist):
        __slots__ = ("_histUp", "_histDown")
        def __init__(self, hist, systVar):
            super(ShapeSystVar.ForHist, self).__init__(hist, systVar)
            self._histUp = None
            self._histDown = None
        @lazyload
        def histUp(self):
            return self._findVarHist("up")
        @lazyload
        def histDown(self):
            return self._findVarHist("down")
        def _findVarHist(self, vari):
            variHistName = "{0}__{1}{2}".format(self.hist.name, self.systVar.name, vari)
            if self.hist.tFile.Get(variHistName):
                return self.hist.clone(name=variHistName)
            else: ## try to find the file
                import os.path
                fullpath = self.hist.tFile.GetPath().split(":")[0]
                variPath = os.path.join(os.path.dirname(fullpath), "{0}__{1}{2}.root".format(os.path.splitext(os.path.basename(fullpath))[0], self.systVar.name, vari))
                if os.path.exists(variPath):
                    from cppyy import gbl
                    vf = gbl.TFile.Open(variPath)
                    if ( not vf ) or vf.IsZombie() or ( not vf.IsOpen() ):
                        raise IOError("Could not open file '{}' correctly".format(variPath))
                    if vf.Get(self.hist.name):
                        return self.hist.clone(tfile=vf)
                    else:
                        logger.error("Could not find '{0}' in file '{1}'".format(self.hist.name, variPath))
                        #raise KeyError()
                else:
                    pass ## fail quietly
                    #print("Path '{}' does not exist".format(variPath))
                    #raise IOError("Path '{}' does not exist".format(variPath))
                #print("Warning: could not find variation hist of {0} for {1}, assuming no variation then".format(self.hist, self.systVar.name))
                return self.hist
        @property
        def up(self):
            return self.histUp.contents
        @property
        def down(self):
            return self.histDown.contents
