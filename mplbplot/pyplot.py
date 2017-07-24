"""
pyplot-like methods that also support a ROOT object as first argument

hist, plot, errorbar, text, contour, contourf, and pcolor methods
are defined as wrappers around the matplotlib ones, and delegate
to those defined in this package for TH1, TH2 and TGraph.

Example:
>>> from matplotlib.pyplot import *
>>> from mplbplot.pyplot import *
>>> subplots(num="MyPlots")
>>> h1 = ROOT.TH1F(...)
>>> hist(h1, histtype="step", color="r")
>>> g1 = ROOT.TGraphAsymErrors(...)
>>> errorbar(g1, fmt="ko")

Available methods:
  For one-dimensional histograms (TH1*) only:
   - hist (HIST option)
  For one-dimensional histograms (TH1*) and TGraph:
   - plot (P and L option; full documentation: __plot__ methods of TH1 and TGraph)
   - errorbar (all E options; full documentation: __errorbar__ methods of TH1 and TGraph)
  For one- and two-dimensional histograms:
   - text (TEXT option; full documentation: __text__ methods of TH1 and TH2)
  For two-dimensional histograms:
   - contour, contourf (CONT), and color (COLZ)
"""
__all__ = ("hist", "plot", "errorbar", "text", "contour", "contourf", "pcolor")

import matplotlib.pyplot as plt
import ROOT

import .draw_th1
import .draw_th2
import .draw_tgraph
for imod in (draw_th1, draw_tgraph, draw_th2):
    imod._addDecorations()

def plot(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.plot that also takes TH1 and TGraph

    see TH1.__plot__, TGraph.__plot__, or matplotlib.pyplot.plot for details
    """
    if isinstance(first, ROOT.TH1) or isinstance(first, ROOT.TGraph):
        kwargs["axes"] = plt.gca()
        return first.__plot__(*args, **kwargs)
    else:
        return plt.plot(first, *args, **args)

def errorbar(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.errorbar that also takes TH1 and TGraph

    see TH1.__errorbar__, TGraph.__errorbar__, or matplotlib.pyplot.errorbar for details
    """
    if isinstance(first, ROOT.TH1) or isinstance(first, ROOT.TGraph):
        kwargs["axes"] = plt.gca()
        return first.__errorbar__(*args, **kwargs)
    else:
        return plt.errorbar(first, *args, **args)

def text(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.text that also takes TH1, TH2, and TGraph

    see TH1.__text__, TH2.__text__, TGraph.__text__, or matplotlib.pyplot.text for details
    """
    if isinstance(first, ROOT.TH1) or isinstance(first, ROOT.TGraph):
        kwargs["axes"] = plt.gca()
        return first.__text__(*args, **kwargs)
    else:
        return plt.text(first, *args, **args)

def hist(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.hist that also takes TH1

    see mplbplot.draw_th1.hist or matplotlib.pyplot.hist for details
    """
    if isinstance(first, ROOT.TH1):
        kwargs["axes"] = plt.gca()
        return draw_th1.hist(first, *args, **kwargs)
    else:
        return plt.hist(first, *args, **args)

def contour(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.contour that also takes TH2

    see mplbplot.draw_th2.contour or matplotlib.pyplot.contour for details
    """
    if isinstance(first, ROOT.TH2):
        kwargs["axes"] = plt.gca()
        return draw_th2.contour(first, *args, **kwargs)
    else:
        return plt.contour(first, *args, **args)

def contourf(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.contourf that also takes TH2

    see mplbplot.draw_th2.contourf or matplotlib.pyplot.contourf for details
    """
    if isinstance(first, ROOT.TH2):
        kwargs["axes"] = plt.gca()
        return draw_th2.contourf(first, *args, **kwargs)
    else:
        return plt.contourf(first, *args, **args)

def pcolor(first, *args, **kwargs):
    """
    Wrapper around matplotlib.pyplot.pcolor that also takes TH2

    see mplbplot.draw_th2.pcolor or matplotlib.pyplot.pcolor for details
    """
    if isinstance(first, ROOT.TH2):
        kwargs["axes"] = plt.gca()
        return draw_th2.pcolor(first, *args, **kwargs)
    else:
        return plt.pcolor(first, *args, **args)
