"""
Systematics classes (based on plotIt)
"""
__all__ = ("HistoKey", "SystVarsForHist",
           "SystVar", "ParameterizedSystVar", "ConstantSystVar", "LogNormalSystVar", "ShapeSystVar"
          )

import itertools
import histo_utils as h1u

class HistoKey(object):
    """
    TH1F wrapper to keep track of origin file, name and transformation

    Will lazily load (and cache) the object from the TFile,
    and apply scaling and rebinning as needed at that point.
    """
    """ Small wrapper around TH1, to keep track of origin file, name and transformation (scale and rebin) """
    __slots__ = ("tfile", "name", "scale", "rebin", "xOverflowRange", "_obj")
    def __init__(self, tfile, name, scale=1., rebin=1, xOverflowRange=None):
        """ Constructor

        Argments:
          tfile             TFile reference
          name              name of the histogram key inside tfile
        Keyword arguments:
          scale             normalization scale to apply (relative)
          rebin             number of bins to group
          xOverflowRange    visible range of the x-axis (bins outside,
                            including histogram overflows, will be added
                            to the first and last bin inside)
        """
        self.tfile = tfile
        self.name = name
        self.scale = scale
        self.rebin = rebin
        self.xOverflowRange = xOverflowRange
        self._obj = None
    def __repr__(self):
        return "HistoKey({0!r}, {1!r}{2})".format(self.tfile, self.name, (", ".join(("", "scale={0:f}".format(self.scale), "rebin={0:d}".format(self.rebin), "xOverflowRange={0}".format(repr(self.xOverflowRange))))))
    def clone(self, tfile=None, name=None, scale=None, rebin=None, xOverflowRange=None):
        """ Modifying clone method

        keyword arguments correspond to the constructor arguments.
        Will make a deep copy (except for the tfile)
        """
        return HistoKey( tfile if tfile is not None else self.tfile
                       , name if str(name) is not None else self.name
                       , scale=(scale if scale is not None else self.scale )
                       , rebin=(rebin if rebin is not None else self.rebin )
                       , xOverflowRange=(tuple(xOverflowRange) if xOverflowRange is not None else self.xOverflowRange )
                       )

    def _get(self):
        if ( not self.tfile ) or self.tfile.IsZombie() or ( not self.tfile.IsOpen() ):
            raise RuntimeError("File '{}'cannot be read".format(self.tfile))
        res = self.tfile.Get(self.name)
        if not res:
            raise KeyError("Could not retrieve key '{0}' from file {1!r}".format(self.name, self.tfile))
        if ( self.scale != 1. ) or ( self.rebin != 1 ) or ( self.xOverflowRange is not None ):
            res = h1u.cloneHist(res)
            if self.xOverflowRange is not None:
                res.GetXaxis().SetRangeUser(self.xOverflowRange[0], self.xOverflowRange[1])
                from histo_utils import addOverflow
                addOverflow(res, res.GetXaxis().GetFirst(), True )
                addOverflow(res, res.GetXaxis().GetLast() , False)
            if self.scale != 1.:
                res.Scale(self.scale)
            if self.rebin != 1:
                res.Rebin(self.rebin)
        self._obj = res
    @property
    def obj(self):
        """ the underlying TH1 object """
        if not self._obj:
            self._get()
        return self._obj
    def __getattr__(self, name):
        return getattr(self.obj, name)

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
    def __repr_args(self):
        return (self.name,)
    def __repr_kwargs(self):
        return tuple((["pretty_name"] if self.pretty_name != self.name else [])+(["on"] if self.on != SystVar.default_filter else []))
    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, ", ".join(itertools.chain((repr(a) for a in self.__repr_args()), ("{0}={1!r}".format(k,getattr(self, k)) for k in self.__repr_kwargs()))))

    def forHist(self, hist):
        """ get variation for hist """
        return self.__class__.ForHist(hist, self)

    class ForHist(object):
        """ Interface & base for systematic variation for a single histogram """
        __slots__ = ("hist", "systVar")
        def __init__(self, hist, systVar):
            self.hist = hist
            self.systVar = systVar
        def nom(self, i):
            """ Nominal value for bin i """
            pass
        def up(self, i):
            """ Up variation for bin i """
            pass
        def down(self, i):
            """ Down variation for bin i """
            pass

import collections
class SystVarsForHist(collections.Mapping):
    """ dict-like object to assign as systVars to an entry

    (parent is the actual dictionary with SystVars) """
    __slots__ = ("hist", "parent")
    def __init__(self, hist, parent):
        self.hist = hist
        self.parent = parent
    def __getitem__(self, ky):
        return self.parent[ky].forHist(self.hist)
    def __iter__(self):
        for systVar in self.parent.iterkeys():
            yield systVar
    def __len__(self):
        return len(self.parent)

class ParameterizedSystVar(SystVar):
    """ base for constant etc. """
    def __init__(self, name, pretty_name=None, on=SystVar.default_filter):
        super(ParameterizedSystVar, self).__init__(name, pretty_name=pretty_name, on=on)
    def nom(self, hist, i):
        pass
    def up(self, hist, i):
        pass
    def down(self, hist, i):
        pass

    class ForHist(SystVar.ForHist):
        """ delegate everything to the corresponding systVar methods """
        __slots__ = tuple()
        def __init__(self, hist, systVar):
            super(ParameterizedSystVar.ForHist, self).__init__(hist, systVar)
        def nom(self, i):
            return self.systVar.nom(self.hist, i)
        def up(self, i):
            return self.systVar.up(self.hist, i)
        def down(self, i):
            return self.systVar.down(self.hist, i)

class ConstantSystVar(ParameterizedSystVar):
    """ constant scale up/down (given as the relative up variation, e.g. 1.2 for 20%) """
    def __init__(self, name, value, pretty_name=None, on=SystVar.default_filter):
        self.value = value
        super(ConstantSystVar, self).__init__(name, pretty_name=pretty_name, on=on)
    def __repr_args(self):
        return (self.name, self.value)

    def nom(self, hist, i):
        return hist.GetBinContent(i)
    def up(self, hist, i):
        return self.nom(hist, i)*self.value
    def down(self, hist, i):
        return self.nom(hist, i)*(2-self.value)

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

    def nom(self, hist, i):
        return hist.GetBinContent(i)
    def up(self, hist, i):
        return self.nom(hist, i)*self.value_up
    def down(self, hist, i):
        return self.nom(hist, i)*self.value_down

class ShapeSystVar(SystVar):
    """ for shapes """
    def __init__(self, name, pretty_name=None, on=SystVar.default_filter):
        self.name = name
        super(ShapeSystVar, self).__init__(name, pretty_name=pretty_name, on=on)

    class ForHist(SystVar.ForHist):
        def __init__(self, hist, systVar):
            super(ShapeSystVar.ForHist, self).__init__(hist, systVar)
            self.histUp = self._findVarHist("up")
            self.histDown = self._findVarHist("down")
        def _findVarHist(self, vari):
            variHistName = "{0}__{1}{2}".format(self.hist.name, self.systVar.name, vari)
            if self.hist.tfile.Get(variHistName):
                return self.hist.clone(name=variHistName)
            else: ## try to find the file
                import os.path
                fullpath = self.hist.tfile.GetPath().split(":")[0]
                variPath = os.path.join(os.path.dirname(fullpath), "{0}__{1}{2}.root".format(os.path.splitext(os.path.basename(fullpath))[0], self.systVar.name, vari))
                if os.path.exists(variPath):
                    from cppyy import gbl
                    vf = gbl.TFile.Open(variPath)
                    if ( not vf ) or vf.IsZombie() or ( not vf.IsOpen() ):
                        raise IOError("Could not open file '{}' correctly".format(variPath))
                    if vf.Get(self.hist.name):
                        return self.hist.clone(tfile=vf)
                    else:
                        print "Could not find '{0}' in file '{1}'".format(self.hist.name, variPath)
                        #raise KeyError()
                else:
                    pass ## fail quietly
                    #print "Path '{}' does not exist".format(variPath)
                    #raise IOError("Path '{}' does not exist".format(variPath))
                #print "Warning: could not find variation hist of {0} for {1}, assuming no variation then".format(self.hist, self.systVar.name)
                return self.hist
        def nom(self, i):
            return self.hist.GetBinContent(i)
        def up(self, i):
            return self.histUp.GetBinContent(i)
        def down(self, i):
            return self.histDown.GetBinContent(i)

if __name__ == "__main__": ## quick test of the basic functionality
    import ROOT
    ROOT.PyConfig.IgnoreCommandLineOptions = True
    from cppyy import gbl
    aHist = HistoKey(gbl.TFile.Open("aFile"), "aName", scale=.5) ## aName__frup and aName__frdown are assumed to be also there
    print aHist.obj
    systTab = {"fr" : ShapeSystVar("fr"), "lumi" : ConstantSystVar(1.06)}
    histSysTab = SystVarsForHist(aHist, systTab)
    systForHist = histSysTab["fr"]
    print systForHist.nom(3), systForHist.up(3), systForHist.down(3)
    otherSystHi = histSysTab["lumi"]
    print otherSystHi.nom(3), otherSystHi.up(3), otherSystHi.down(3)
