"""
Matplotlib draw methods for TH2

The contour, contourf, pcolor, and text methods are available.
When used through the decorators with mplbplot.plot (recommended),
the methods will be called rcontour, rcontourf, rpcolor, and rtext,
and the documentation for the latter is available through TH2.__text__.
"""
__all__ = ("countour", "contourf", "pcolor", "text")

import numpy as np
import itertools

from .decorators import bins
from .draw_th1 import _getBinCoordinate

def contour( histo, *args, **kwargs ):
    """
    Wrapper around axes.contour for TH2, replacement for ROOT's CONT option

    Bin centers (or edges, if specified with useEdge(X|Y)="lower" or "upper") and heights are taken from the histogram,
    and fill the X, Y and Z arguments of contour, any other arguments are passed on to contour.
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    """
    # get keyword arguments
    axes = kwargs.pop("axes", None)
    volume = kwargs.pop("volume", False)
    useEdgeX = kwargs.pop("useEdgeX", None)
    useEdgeY = kwargs.pop("useEdgeY", None)

    height = ( lambda b : b.contentH ) if volume else ( lambda b : b.content )
    getX = _getBinCoordinate(useEdgeX)
    getY = _getBinCoordinate(useEdgeY)

    x = np.array([ getX(b) for b in bins(histo.GetXaxis()) ])
    y = np.array([ getY(b) for b in bins(histo.GetYaxis()) ])
    z = np.array([ height(b) for b in bins(histo) ]).reshape((histo.GetNbinsX(), histo.GetNbinsY())).T

    return axes.contour( x, y, z, *args, **kwargs)

def contourf( histo, *args, **kwargs ):
    """
    Wrapper around axes.contourf for TH2, replacement for ROOT's CONT option

    Bin centers (or edges, if specified with useEdge(X|Y)="lower" or "upper") and heights are taken from the histogram,
    and fill the X, Y and Z arguments of contourf, any other arguments are passed on to contourf.
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    """
    # get keyword arguments
    axes = kwargs.pop("axes", None)
    volume = kwargs.pop("volume", False)
    useEdgeX = kwargs.pop("useEdgeX", None)
    useEdgeY = kwargs.pop("useEdgeY", None)

    height = ( lambda b : b.contentH ) if volume else ( lambda b : b.content )
    getX = _getBinCoordinate(useEdgeX)
    getY = _getBinCoordinate(useEdgeY)

    x = np.array([ getX(b) for b in bins(histo.GetXaxis()) ])
    y = np.array([ getY(b) for b in bins(histo.GetYaxis()) ])
    z = np.array([ height(b) for b in bins(histo) ]).reshape((histo.GetNbinsX(), histo.GetNbinsY())).T

    return axes.contourf( x, y, z, *args, **kwargs)

def pcolor( histo, *args, **kwargs ):
    """
    Wrapper around axes.pcolor for TH2, replacement for ROOT's COLZ option

    Bin edges and heights are taken from the histogram, and fill the X, Y and Z arguments of pcolor;
    any other arguments are passed on to pcolor.
    If the "volume" option is set to True, the height is determined as the bin contents divided by its width
    (such that the volume is proportional to the contents, rather than the height).
    """
    # get keyword arguments
    axes = kwargs.pop("axes", None)
    volume = kwargs.pop("volume", False)

    height = ( lambda b : b.contentH ) if volume else ( lambda b : b.content )

    xEdges = np.array( [ bins(histo.GetXaxis())[1].lowEdge ] + [ b.upEdge for b in bins(histo.GetXaxis()) ] )
    yEdges = np.array( [ bins(histo.GetYaxis())[1].lowEdge ] + [ b.upEdge for b in bins(histo.GetYaxis()) ] )
    z = np.array([ height(b) for b in bins(histo) ]).reshape((histo.GetNbinsX(), histo.GetNbinsY())).T

    return axes.pcolormesh(xEdges, yEdges, z, *args, **kwargs)

def text( histo, formatFun="{0:.0f}".format, axes=None, empty=False, useEdgeX=None, useEdgeY=None, **kwargs ):
    """
    Wrapper around axes.text for every bin of a TH2, replacement for ROOT's TEXT option

    Bin centers (or edges, if specified with useEdge(X|Y)="lower" or "upper") and heights are taken from the histogram.
    Empty bins are kept if "empty" is set to True.
    formatFun is called on every bin to determine the string to display.
    All keyword arguments are passed on to axes.text, but
    if no defaults are specified for ha/horizontalalignment,
    va/verticalalignment and rotation, they are set to "center",
    "center" and "horizontal", respectively.
    """
    getX = _getBinCoordinate(useEdgeX, "x")
    getY = _getBinCoordinate(useEdgeY, "y")

    ## set some defaults differently
    if "ha" not in kwargs and "horizontalalignment" not in kwargs:
        kwargs["ha"] = "center"
    if "va" not in kwargs and "verticalalignment" not in kwargs:
        kwargs["va"] = "center"
    if "rotation" not in kwargs:
        kwargs["rotation"] = "horizontal"

    return list( axes.text(getX(b), getY(b), formatFun(b), **kwargs) for b in bins(histo) if empty or b.content != 0. )

def _addDecorations():
    """ used by mplbplot.plot for loading all decorations """
    import matplotlib.axes
    import matplotlib.pyplot as plt
    # decorate ax.rcontour(hist, ...), plt.rcontour(hist, ...)
    def rcontour_ax(self, obj, *args, **kwargs):
        return contour(obj, *args, axes=self, **kwargs)
    rcontour_ax.__doc__ = contour.__doc__
    matplotlib.axes.Axes.rcontour = rcontour_ax
    def rcontour_plt(obj, *args, **kwargs):
        return contour(obj, *args, axes=plt.gca(), **kwargs)
    rcontour_plt.__doc__ = contour.__doc__
    plt.rcontour = rcontour_plt
    # decorate ax.rcontourf(hist, ...), plt.rcontourf(hist, ...)
    def rcontourf_ax(self, obj, *args, **kwargs):
        return contourf(obj, *args, axes=self, **kwargs)
    rcontourf_ax.__doc__ = contourf.__doc__
    rcontourf_ax.__doc__ = contourf.__doc__
    matplotlib.axes.Axes.rcontourf = rcontourf_ax
    def rcontourf_plt(obj, *args, **kwargs):
        return contourf(obj, *args, axes=plt.gca(), **kwargs)
    rcontourf_plt.__doc__ = contourf.__doc__
    plt.rcontourf = rcontourf_plt
    # decorate ax.rpcolor(hist, ...), plt.rpcolor(hist, ...)
    def rpcolor_ax(self, obj, *args, **kwargs):
        return pcolor(obj, *args, axes=self, **kwargs)
    rpcolor_ax.__doc__ = pcolor.__doc__
    matplotlib.axes.Axes.rpcolor = rpcolor_ax
    def rpcolor_plt(obj, *args, **kwargs):
        return pcolor(obj, *args, axes=plt.gca(), **kwargs)
    rpcolor_plt.__doc__ = pcolor.__doc__
    plt.rpcolor = rpcolor_plt

    import ROOT

    ROOT.TH2.__text__ = text
