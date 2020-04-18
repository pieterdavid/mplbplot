from __future__ import absolute_import
"""
Decorate matplotlib.pyplot with draw methods for ROOT objects

Designed for use with the matlab-style matplotlib pyplot API.
The methods are similar to the default matplotlib ones,
and are prefixed with the letter "r" ("rhist" for "hist" with a TH1).

Usage:
>>> from matplotlib import pyplot as plt
>>> import mplbplot.decoratePyplot
>>> plt.subplots(num="MyPlots")
>>> h1 = ROOT.TH1F(...)
>>> plt.rhist(h1, histtype="step", color="r", volume=True)
>>> g1 = ROOT.TGraphAsymErrors(...)
>>> plt.rerrorbar(g1, fmt="ko")

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

from . import draw_th1    ## add rhist and implementations for rplot, rerrorbar and rtext
from . import draw_tgraph ## add implementations for rplot and rerrorbar
from . import draw_th2    ## add rcontour, rcontourf, rpcolor and implementation for rtext
for imod in (draw_th1, draw_tgraph, draw_th2):
    imod._addDecorations()

import matplotlib.pyplot as plt

# Single dispatch for plt.rplot(obj, ...)
def rplot_plt(obj, *args, **kwargs):
    return obj.__plot__(*args, axes=plt.gca(), **kwargs)
plt.rplot = rplot_plt

# Single dispatch for plt.rerrorbar(obj, ...)
def rerrorbar_plt(obj, *args, **kwargs):
    return obj.__errorbar__(*args, axes=plt.gca(), **kwargs)
plt.rerrorbar = rerrorbar_plt

# Single dispatch for plt.rtext(obj, ...)
def rtext_plt(obj, *args, **kwargs):
    return obj.__text__(*args, axes=plt.gca(), **kwargs)
plt.rtext = rtext_plt

# decorate plt.rhist(hist, ...)
def rhist_plt(obj, *args, **kwargs):
    return draw_th1.hist(obj, *args, axes=plt.gca(), **kwargs)
rhist_plt.__doc__ = draw_th1.hist.__doc__
plt.rhist = rhist_plt

# decorate plt.rcontour(hist, ...)
def rcontour_plt(obj, *args, **kwargs):
    return draw_th2.contour(obj, *args, axes=plt.gca(), **kwargs)
rcontour_plt.__doc__ = draw_th2.contour.__doc__
plt.rcontour = rcontour_plt

# decorate plt.rcontourf(hist, ...)
def rcontourf_plt(obj, *args, **kwargs):
    return draw_th2.contourf(obj, *args, axes=plt.gca(), **kwargs)
rcontourf_plt.__doc__ = draw_th2.contourf.__doc__
plt.rcontourf = rcontourf_plt

# decorate plt.rpcolor(hist, ...)
def rpcolor_plt(obj, *args, **kwargs):
    return draw_th2.pcolor(obj, *args, axes=plt.gca(), **kwargs)
rpcolor_plt.__doc__ = draw_th2.pcolor.__doc__
plt.rpcolor = rpcolor_plt
