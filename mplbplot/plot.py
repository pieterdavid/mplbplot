"""
User-facing module: adds methods to matplotlib.axes.Axes and the matplotlib.pyplot module

Usage:
>>> import matplotlib.pyplot as plt
>>> import ....plot
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
   - rtext (TEXT option; full documentation: __errorbar__ methods of TH1 and TH2)
  For two-dimensional histograms:
   - rcontour, rcontourf (CONT), and pcolor (COLZ)
"""
__all__ = ()

import matplotlib.axes
import matplotlib.pyplot as plt

# Single dispatch for ax.rplot(obj, ...) and plt.rplot(obj, ...)
def rplot_ax(self, obj, *args, **kwargs):
    return obj.__plot__(*args, axes=self, **kwargs)
matplotlib.axes.Axes.rplot = rplot_ax
def rplot_plt(obj, *args, **kwargs):
    return obj.__plot__(*args, axes=plt.gca(), **kwargs)
plt.rplot = rplot_plt

# Single dispatch for ax.rerrorbar(obj, ...) and plt.rerrorbar(obj, ...)
def rerrorbar_ax(self, obj, *args, **kwargs):
    return obj.__errorbar__(*args, axes=self, **kwargs)
matplotlib.axes.Axes.rerrorbar = rerrorbar_ax
def rerrorbar_plt(obj, *args, **kwargs):
    return obj.__errorbar__(*args, axes=plt.gca(), **kwargs)
plt.rerrorbar = rerrorbar_plt

# Single dispatch for ax.rtext(obj, ...) and plt.rtext(obj, ...)
def rtext_ax(self, obj, *args, **kwargs):
    return obj.__text__(*args, axes=self, **kwargs)
matplotlib.axes.Axes.rtext = rtext_ax
def rtext_plt(obj, *args, **kwargs):
    return obj.__text__(*args, axes=plt.gca(), **kwargs)
plt.rtext = rtext_plt

import draw_th1    ## add rhist and implementations for rplot, rerrorbar and rtext
import draw_tgraph ## add implementations for rplot and rerrorbar
import draw_th2    ## add rcontour, rcontourf, rpcolor and implementation for rtext
for imod in (draw_th1, draw_tgraph, draw_th2):
    imod._addDecorations()
