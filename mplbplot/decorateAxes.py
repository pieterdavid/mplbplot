"""
Decorate matplotlib.axes.Axes with draw methods for ROOT objects

Designed for use with the object-oriented matplotlib API.
The methods are similar to the default matplotlib ones,
and are prefixed with the letter "r" ("rhist" for "hist" with a TH1).

Usage:
>>> from matplotlib import pyplot as plt
>>> import mplbplot.decorateAxes
>>> fig,ax = plt.subplots(num="MyPlots")
>>> h1 = ROOT.TH1F(...)
>>> ax.rhist(h1, histtype="step", color="r", volume=True)
>>> g1 = ROOT.TGraphAsymErrors(...)
>>> ax.rerrorbar(g1, fmt="ko")

Available methods:
  For one-dimensional histograms (TH1*) only:
   - rhist (HIST option)
  For one-dimensional histograms (TH1*) and TGraph:
   - rplot (P and L option; full documentation: __plot__ methods of TH1 and TGraph)
   - rerrorbar (all E options; full documentation: __errorbar__ methods of TH1 and TGraph)
  For one- and two-dimensional histograms:
   - rtext (TEXT option; full documentation: __text__ methods of TH1 and TH2)
  For two-dimensional histograms:
   - rcontour, rcontourf (CONT), and pcolor (COLZ)
"""
__all__ = ()

import draw_th1    ## add rhist and implementations for rplot, rerrorbar and rtext
import draw_tgraph ## add implementations for rplot and rerrorbar
import draw_th2    ## add rcontour, rcontourf, rpcolor and implementation for rtext
for imod in (draw_th1, draw_tgraph, draw_th2):
    imod._addDecorations()

import matplotlib.axes

# Single dispatch for ax.rplot(obj, ...)
def rplot_ax(self, obj, *args, **kwargs):
    return obj.__plot__(*args, axes=self, **kwargs)
matplotlib.axes.Axes.rplot = rplot_ax

# Single dispatch for ax.rerrorbar(obj, ...)
def rerrorbar_ax(self, obj, *args, **kwargs):
    return obj.__errorbar__(*args, axes=self, **kwargs)
matplotlib.axes.Axes.rerrorbar = rerrorbar_ax

# Single dispatch for ax.rtext(obj, ...)
def rtext_ax(self, obj, *args, **kwargs):
    return obj.__text__(*args, axes=self, **kwargs)
matplotlib.axes.Axes.rtext = rtext_ax

# decorate ax.rhist(hist, ...)
def rhist_ax(self, obj, *args, **kwargs):
    return draw_th1.hist(obj, *args, axes=self, **kwargs)
rhist_ax.__doc__ = draw_th1.hist.__doc__
matplotlib.axes.Axes.rhist = rhist_ax

# decorate ax.rcontour(hist, ...)
def rcontour_ax(self, obj, *args, **kwargs):
    return draw_th2.contour(obj, *args, axes=self, **kwargs)
rcontour_ax.__doc__ = draw_th2.contour.__doc__
matplotlib.axes.Axes.rcontour = rcontour_ax

# decorate ax.rcontourf(hist, ...)
def rcontourf_ax(self, obj, *args, **kwargs):
    return draw_th2.contourf(obj, *args, axes=self, **kwargs)
rcontourf_ax.__doc__ = draw_th2.contourf.__doc__
matplotlib.axes.Axes.rcontourf = rcontourf_ax

# decorate ax.rpcolor(hist, ...)
def rpcolor_ax(self, obj, *args, **kwargs):
    return draw_th2.pcolor(obj, *args, axes=self, **kwargs)
rpcolor_ax.__doc__ = draw_th2.pcolor.__doc__
matplotlib.axes.Axes.rpcolor = rpcolor_ax
