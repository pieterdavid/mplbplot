"""
Matplotlib draw methods for TGraph

The plot and errorbar methods are available.
When used through the decorators with mplbplot.plot (recommended),
the methods will be called rplot and rerrorbar,
and the full documentation is available through
TGraph.__plot__ and TGraph.__errorbar__.
"""
__all__ = ("plot", "errorbar")

from .decorators import points

def plot( graph, fmt=None, axes=None, **kwargs ):
    """
    Wrapper around axes.plot for TGraph, replacement for ROOT's P and L options

    Point coordinates are taken from the graph.
    """
    x, y = zip(*[ (p.x, p.y) for p in points(graph) ])

    return axes.plot( x, y, fmt, **kwargs )

def errorbar( graph, axes=None, xErrors=True, kind="bar", removeZero=False, **kwargs ):
    """
    Wrapper around axes.errorbar for TGraph, replacement for ROOT's E option (with P and/or L at a time, in case kind is bar)

    Point coordinates and errors are taken from the graph.
    The type of error visualisation can be set by setting kind="bar", "box" or "band".
    x errors can be turned off by setting xErrors to False (ignored in case kind is box; meaningless in case kind is band).
    Points with y=0 can be removed by passing the option removeZero=True
    """
    if kind == "bar":
        x,xle,xue,y,yle,yue = zip(*[ (p.x, p.xLowError, p.xHighError, p.y, p.yLowError, p.yHighError) for p in points(graph) if not removeZero or p.y != 0. ])
        return axes.errorbar(x, y, yerr=(yle, yue), xerr=( (xle,xue) if xErrors else None ), **kwargs)
    elif kind == "box":
        import matplotlib.patches
        return [ axes.add_patch( matplotlib.patches.Rectangle(
                        (p.x-p.xLowError, p.y-p.yLowError), ## left bottom
                        width=(p.xLowError+p.xHighError), height=(p.yLowError+p.yHighError),
                        **kwargs ) )
                    for p in points(graph) if not removeZero or p.y != 0. ]
    elif kind == "band":
        x,yLow,yHigh = zip(*[ (p.x, p.y-p.yLowError, p.y+p.yHighError) for p in points(graph) if not removeZero or p.y != 0. ])
        return axes.fill_between( x, yLow, y2=yHigh, **kwargs )

def _addDecorations():
    """ load decorators for draw methods that need dispatch """

    import ROOT
    ROOT.TGraph.__plot__ = plot
    ROOT.TGraph.__errorbar__ = errorbar
