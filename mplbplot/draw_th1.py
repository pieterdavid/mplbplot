"""
Matplotlib draw methods for TH1

The hist, plot, errorbar, and text methods are available,
see their respective documentation for more details.
When used through the decorators with mplbplot.plot (recommended),
the methods will be called rhist, rplot, rerrorbar and rtext,
and the documentation for the latter three is available through
TH1.__plot__, TH1.__errorbar__, and TH1.__text__.
"""
__all__ = ("hist", "plot", "errorbar", "text", "IncompatibleAxesError")

from itertools import izip_longest

from .decorators import bins

def _equal_lists(a,b):
    return all( ia == ib for ia,ib in izip_longest(a,b) )

def xBinEdges(h):
    return [ bins(h)[1].xLowEdge ] + [ b.xUpEdge for b in bins(h) ]

class IncompatibleAxesError(IndexError):
    def __init__(self, hA, hB):
        self.hA = hA
        self.hB = hB
    def __str__(self):
        return "{a:s} and {b:s} have incompatible axes".format(a=self.hA, b=self.hB)

def hist( histo, axes=None, volume=False, **kwargs ):
    """
    Wrapper around axes.hist
 
    The histogram(s) is (are) transformed into the suitable format, and the bins argument set.
    In case multiple histograms are given, a check is done to make sure the axes are equal.
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    """
    height = ( lambda b : b.contentH ) if volume else ( lambda b : b.content )

    if hasattr(histo, "__iter__") and len(histo) > 0:
        firstEdges = xBinEdges(histo[0])
        firstCenters = [ b.xCenter for b in bins(histo[0]) ]
        # check compatibility of axes
        if not all( _equal_lists(xBinEdges(ih), firstEdges) for ih in histo ):
            raise Exception
        return axes.hist( [ firstCenters for ih in histo ], weights=[ [ height(b) for b in bins(ih) ] for ih in histo ], bins=firstEdges, **kwargs )
    else:
        return axes.hist( [ b.xCenter for b in bins(histo) ], weights=[ height(b) for b in bins(histo) ], bins=xBinEdges(histo), **kwargs )

def _getBinCoordinate( edge=None, axis=None ):
    """
    Get the right bin coordinates (helper method for draw_P and similar methods)
    """
    if edge == "lower":
        edgePart = "lowEdge"
    elif edge == "upper":
        edgePart = "upEdge"
    else:
        edgePart = "center"
    if axis:
        attrName = "".join((axis, edgePart[:1].upper(), edgePart[1:]))
    else:
        attrName = edgePart
    return ( lambda b : getattr(b, attrName) )

def plot( histo, fmt=None, axes=None, empty=False, volume=False, useEdge=None, **kwargs ):
    """
    Wrapper around axes.plot for TH1, replacement for ROOT's P and L options

    Bin centers (or edges, if specified with useEdge="lower" or "upper") and heights are taken from the histogram.
    Empty bins are kept if "empty" is set to True. x errors can be turned off by setting "xErrors" to True.
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    """
    height = ( lambda b : b.contentH ) if volume else ( lambda b : b.content )
    getX = _getBinCoordinate(useEdge, "x")

    x, y = zip(*[ (getX(b), height(b)) for b in bins(histo) if empty or b.content != 0. ])

    return axes.plot( x, y, fmt, **kwargs )

def errorbar( histo, axes=None, empty=False, volume=False, useEdge=None, xErrors=True, kind="bar", **kwargs ):
    """
    Wrapper around axes.errorbar for TH1, replacement for ROOT's E option (with P and/or L at a time, in case kind is bar)

    Bin centers (or edges, if specified with useEdge="lower" or "upper"), heights and errors are taken from the histogram.
    The type of error visualisation can be set by setting kind="bar", "box" or "band".
    Empty bins are kept if "empty" is set to True. x errors can be turned off by setting xErrors to False (ignored in case kind is box; meaningless in case kind is band).
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    """
    height       = ( lambda b : b.contentH  ) if volume else ( lambda b : b.content  )
    heightUpErr  = ( lambda b : b.upErrorH  ) if volume else ( lambda b : b.upError  )
    heightLowErr = ( lambda b : b.lowErrorH ) if volume else ( lambda b : b.lowError )
    getX = _getBinCoordinate(useEdge, "x")

    if kind == "bar":
        x,xe,y,yle,yue = zip(*[ (getX(b), .5*b.xWidth, height(b), heightLowErr(b), heightUpErr(b)) for b in bins(histo) if empty or b.content != 0. ])
        return axes.errorbar(x, y, yerr=(yle, yue), xerr=( xe if xErrors else None ), **kwargs)
    elif kind == "box":
        import matplotlib.patches
        return [ axes.add_patch( matplotlib.patches.Rectangle(
                        (b.xLowEdge, height(b)-heightLowErr(b)), ## left bottom
                        width=b.xWidth, height=heightLowErr(b)+heightUpErr(b),
                        **kwargs ) )
                    for b in bins(histo) if empty or b.content != 0. ]
    elif kind == "band":
        x,yLow,yHigh = zip(*[ (getX(b), height(b)-heightLowErr(b), height(b)+heightUpErr(b)) for b in bins(histo) if empty or b.content != 0. ])
        return axes.fill_between( x, yLow, y2=yHigh, **kwargs )

def text( histo, formatFun="{0:.0f}".format, axes=None, empty=False, volume=False, useEdge=None, **kwargs ):
    """
    Wrapper around axes.text for every bin of a TH1, replacement for ROOT's TEXT option

    Bin centers (or edges, if specified with useEdge="lower" or "upper") and heights are taken from the histogram.
    Empty bins are kept if "empty" is set to True.
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    formatFun is called on every bin to determine the string to display.
    All keyword arguments are passed on to axes.text, but
    if no defaults are specified for ha/horizontalalignment,
    va/verticalalignment and rotation, they are set to "center",
    "center" and "vertical", respectively.
    """
    height = ( lambda b : b.contentH ) if volume else ( lambda b : b.content )
    getX = _getBinCoordinate(useEdge, "x")

    ## set some defaults differently
    if "ha" not in kwargs and "horizontalalignment" not in kwargs:
        kwargs["ha"] = "center"
    if "va" not in kwargs and "verticalalignment" not in kwargs:
        kwargs["va"] = "center"
    if "rotation" not in kwargs:
        kwargs["rotation"] = "vertical"

    return list( axes.text(getX(b), height(b), formatFun(b), **kwargs) for b in bins(histo) if empty or b.content != 0. )

def _addDecorations():
    """ load decorators for draw methods that need dispatch """

    # placeholder to block rplot(TH2) etc.
    def _onlyForTH1():
        raise AttributeError("This method is only for 1D histograms")

    from cppyy import gbl

    gbl.TH1.__plot__ = plot
    gbl.TH2.__plot__ = _onlyForTH1
    gbl.TH3.__plot__ = _onlyForTH1

    gbl.TH1.__errorbar__ = errorbar
    gbl.TH2.__errorbar__ = _onlyForTH1
    gbl.TH3.__errorbar__ = _onlyForTH1

    gbl.TH1.__text__ = text
    gbl.TH2.__text__ = _onlyForTH1
    gbl.TH3.__text__ = _onlyForTH1
