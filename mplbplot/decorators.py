"""
Pythonic access to TH1, TH2 and TGraph data
"""
__all__ = ("bins", "points")

def bins(hist):
    """
    Get access to the bins of a histogram
    
    the returned object can be indexed and iterated over,
    the elements are of the appropriate dimensionality
    """
    return hist.__bins__()

def points(graph):
    """
    Get access to the points of a graph
    
    the returned object can be indexed and iterated over,
    the elements are of the appropriate dimensionality
    """
    return graph.__points__()

from itertools import product

import ROOT

axisBinDescriptors = { "center"   : ROOT.TAxis.GetBinCenter
                     , "lowEdge"  : ROOT.TAxis.GetBinLowEdge
                     , "upEdge"   : ROOT.TAxis.GetBinUpEdge
                     , "width"    : ROOT.TAxis.GetBinWidth
                     , "label"    : ROOT.TAxis.GetBinLabel
                     }
histBinDescriptors = { "content"  : ROOT.TH1.GetBinContent
                     , "error"    : ROOT.TH1.GetBinError
                     , "lowError" : ROOT.TH1.GetBinErrorLow
                     , "upError"  : ROOT.TH1.GetBinErrorUp
                     }

# trivial helper: add doc and return (for lambdas) 
def _addDoc(obj, doc=None):
    obj.__doc__ = doc
    return obj

graphPointDescriptorsPerAxis = { "{0}"          : lambda ax : _addDoc( ( lambda self,i : getattr(ROOT.TGraph, "Get{0}".format(ax.upper()))(self)[i] ),
                                                                        doc="lambda g,i : ROOT.TGraph.Get{0}(g)[i]".format(ax.upper()) )
                               , "{0}Error"     : lambda ax : getattr(ROOT.TGraph, "GetError{0}".format(ax.upper())) 
                               , "{0}HighError" : lambda ax : getattr(ROOT.TGraph, "GetError{0}high".format(ax.upper())) 
                               , "{0}LowError"  : lambda ax : getattr(ROOT.TGraph, "GetError{0}low".format(ax.upper())) 
                               }

################################################################################
# Property helper classes                                                      #
################################################################################

class BinProperty1(property):
    """
    Easily construct many properties of the type

    >>> @property
    >>> def fun(self):
    >>>     return self._h.getter(self._i)
    """
    def __init__( self, accessor, idxAttr ):
        self.accessor = accessor
        self.idxAttr = idxAttr
        property.__init__(self, fget=None, fset=None, fdel=None)
    def __get__( self, obj, objtype=None ):
        if obj is None:
            return self
        return self.accessor(obj._h, getattr(obj, self.idxAttr))

class BinProperty2(property):
    """
    Easily construct many properties of the type

    >>> @property
    >>> def fun(self):
    >>>     return self._h.getter(self._i, self._j)
    """
    def __init__( self, accessor, xIdxAttr, yIdxAttr ):
        self.accessor = accessor
        self.xIdxAttr = xIdxAttr
        self.yIdxAttr = yIdxAttr
        property.__init__(self, fget=None, fset=None, fdel=None)
    def __get__( self, obj, objtype=None ):
        if obj is None:
            return self
        return self.accessor(obj._h, getattr(obj, self.xIdxAttr), getattr(obj, self.yIdxAttr))

################################################################################
# Histogram axis                                                               #
################################################################################

class AxisBin1D(object):
    """
    iterator referring to a bin of an axis
    """
    __slots__ = ("_h", "_i")

    def __init__(self, axis, i):
        self._h = axis
        self._i = i

    def __repr__(self):
        return "AxisBins1D({0})[{1:n}]".format(repr(self._h), self._i)

# AxisBin1D data descriptors
for name, getter in axisBinDescriptors.iteritems():
    prop = BinProperty1(getter, "_i")
    prop.__doc__ = "Bin {n} using ROOT.TAxis.{func}".format(n=name, func=getter.__name__)
    setattr(AxisBin1D, name, prop)

class AxisBins1D(object):
    """
    pythonic access to an axis' bins

    Not strictly a sequence since ROOT's bin numbering is preserved,
    but forward iteration and random access are supported.
    """
    __slots__ = ("_a",)

    def __init__(self, axis):
        self._a = axis

    def __repr__(self):
        return "AxisBins1D({0})".format(repr(self._a))

    def __iter__(self):
        for i in xrange(1,self._a.GetNbins()+1):
            yield AxisBin1D(self._a, i)

    def __len__(self):
        return self._a.GetNbins()
    def __getitem__(self, i):
        return AxisBin1D(self._a, i)

# decorate axis class
def _taxis_bins(self):
    return AxisBins1D(self)
ROOT.TAxis.__bins__ = _taxis_bins

################################################################################
# One-dimensional histograms                                                   #
################################################################################

class HistoBin1D(object):
    """
    iterator referring to a bin of a one-dimensional histogram
    """
    __slots__ = ("_h", "_i")

    def __init__(self, hist, i):
        self._h = hist
        self._i = i

    def __repr__(self):
        return "{0}({1})[{2:n}]".format(self.__class__.__name__, repr(self._h), self._i)

# HistoBin1D data descriptors
for name, getter in histBinDescriptors.iteritems():
    prop = BinProperty1(getter, "_i")
    prop.__doc__ = "Bin {n} using ROOT.TH1.{func}".format(n=name, func=getter.__name__)
    setattr(HistoBin1D, name, prop)
    # height instead of contents
    hGetter = lambda h,i,getter=getter : ( getter(h,i)/h.GetBinWidth(i) )
    hGetterName = "lambda h,i : ROOT.TH1.{0}(h, i) / h.GetBinWidth(i)".format(getter.__name__)
    hProp = BinProperty1(hGetter, "_i")
    hProp.__doc__ = "Bin {n} height using {func}".format(n=name, func=hGetterName)
    setattr(HistoBin1D, "{0}H".format(name), hProp)
# Delegates to X-axis
for name, getter in axisBinDescriptors.iteritems():
    xGetter = lambda h,i,getter=getter : getter(h.GetXaxis(), i)
    xGetterName = "lambda h,i : ROOT.TAxis.{0}(h.GetXaxis(), i)".format(getter.__name__)
    prop = BinProperty1(xGetter, "_i")
    prop.__doc__ = "Bin {n} using {func}".format(n=name, func=xGetterName)
    setattr(HistoBin1D, "x{0}{1}".format(name[:1].upper(),name[1:]), prop)

class HistoBins1D(object):
    """
    pythonic access to a (strictly) one-dimensional histogram's bins

    Not strictly a sequence since ROOT's bin numbering is preserved,
    but forward iteration and random access are supported.
    """
    __slots__ = ("_h",)

    def __init__(self, hist):
        self._h = hist

    def __repr__(self):
        return "HistoBins1D({0})".format(repr(self._h))

    def __iter__(self):
        for i in xrange(1,self._h.GetNbinsX()+1):
            yield HistoBin1D(self._h, i)

    def __len__(self):
        return self._h.GetNbinsX()
    def __getitem__(self, i):
        return HistoBin1D(self._h, i)

# decorate 1D histogram classes
def _th1_bins(self):
    return HistoBins1D(self)
ROOT.TH1.__bins__ = _th1_bins
# placeholder for non-1D subclasses (2D is just below)
ROOT.TH3.__bins__ = property(lambda: AttributeError("3D histograms are not supported yet"))

################################################################################
# Two-dimensional histograms                                                   #
################################################################################

class HistoBin2D(object):
    """
    iterator referring to a bin of a two-dimensional histogram
    """
    __slots__ = ("_h", "_i", "_j")

    def __init__(self, hist, i, j):
        self._h = hist
        self._i = i
        self._j = j

    def __repr__(self):
        return "{0}({1})[{2:n},{3:n}]".format(self.__class__.__name__, repr(self._h), self._i, self._j)

# HistoBin2D data descriptors
for name, getter in histBinDescriptors.iteritems():
    prop = BinProperty2(getter, "_i", "_j")
    prop.__doc__ = "Bin {n} using ROOT.TH2.{func}".format(n=name, func=getter.__name__)
    setattr(HistoBin2D, name, prop)
    # height instead of contents
    hGetter = lambda h,i,j,getter=getter : ( getter(h,i,j)/(h.GetXaxis().GetBinWidth(i)*h.GetYaxis().GetBinWidth(j)) )
    hGetterName = "lambda h,i,j : {0}(h, i, j) / (h.GetXaxis().GetBinWidth(i)*h.GetYaxis().GetBinWidth(j)".format(getter.__name__)
    hProp = BinProperty2(hGetter, "_i", "_j")
    hProp.__doc__ = "Bin {n} height using {func}".format(n=name, func=hGetterName)
    setattr(HistoBin2D, "{0}H".format(name), hProp)
# Delegates to axes
for name, getter in axisBinDescriptors.iteritems():
    # X axis
    xGetter = lambda h,i,getter=getter : getter(h.GetXaxis(), i)
    xGetterName = "lambda h,i : ROOT.TAxis.{0}(h.GetXaxis(), i)".format(getter.__name__)
    xProp = BinProperty1(xGetter, "_i")
    xProp.__doc__ = "Bin {n} using {func}".format(n=name, func=xGetterName)
    setattr(HistoBin2D, "x{0}{1}".format(name[:1].upper(),name[1:]), xProp)
    # Y axis
    yGetter = lambda h,j,getter=getter : getter(h.GetYaxis(), j)
    yGetterName = "lambda h,j : ROOT.TAxis.{0}(h.GetYaxis(), j)".format(getter.__name__)
    yProp = BinProperty1(yGetter, "_j")
    yProp.__doc__ = "Bin {n} using {func}".format(n=name, func=yGetterName)
    setattr(HistoBin2D, "y{0}{1}".format(name[:1].upper(),name[1:]), yProp)

class HistoBins2D(object):
    """
    pythonic access to a (strictly) two-dimensional histogram's bins

    Not strictly a sequence since ROOT's bin numbering is preserved,
    but forward iteration and random access are supported.
    """
    __slots__ = ("_h",)

    def __init__(self, hist):
        self._h = hist

    def __repr__(self):
        return "HistoBins2D({0})".format(repr(self._h))

    def __iter__(self):
        for i, j in product(xrange(1,self._h.GetNbinsX()+1), xrange(1,self._h.GetNbinsY()+1)):
            yield HistoBin2D(self._h, i, j)

    def __len__(self):
        return self._h.GetNbinsX()*self._h.GetNbinsY()
    def __getitem__(self, (i, j) ):
        return HistoBin2D(self._h, i, j)

def _th2_bins(self):
    return HistoBins2D(self)
ROOT.TH2.__bins__ = _th2_bins

################################################################################
# TGraph                                                                       #
################################################################################

class GraphPoint(object):
    """
    iterator referring to a point of a graph
    """
    __slots__ = ("_h", "_i")

    def __init__(self, graph, i):
        self._h = graph
        self._i = i

    def __repr__(self):
        return "GraphPoints({0})[{1:n}]".format(repr(self._h), self._i)

for ax in ("x", "y"):
    for namePat, getterGen in graphPointDescriptorsPerAxis.iteritems():
        name = namePat.format(ax)
        getter = getterGen(ax)
        prop = BinProperty1(getter, "_i")
        prop.__doc__ = "Point {n} using {func}".format(n=name, func=(getter.__name__ if getter.__name__ != "<lambda>" else getter.__doc__))
        setattr(GraphPoint, name, prop)

class GraphPoints(object):
    """
    pythonic access to the points of a graph
    """
    __slots__ = ("_g",)

    def __init__(self, graph):
        self._g = graph

    def __repr__(self):
        return "GraphPoints({0})".format(repr(self._g))

    def __iter__(self):
        for i in xrange(self._g.GetN()):
            yield GraphPoint(self._g, i)

    def __len__(self):
        return self._g.GetN()
    def __getitem__(self, i):
        return GraphPoint(self._g.GetN(), i)

# decorate 1D histogram classes
def _graph_points(self):
    return GraphPoints(self)
ROOT.TGraph.__points__ = _graph_points
