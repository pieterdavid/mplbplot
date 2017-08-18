"""
This notebook shows a few simple examples of how to draw a 1-dimensional ROOT histogram
([TH1F](https://root.cern.ch/doc/master/classTH1F.html)) in [matplotlib](http://matplotlib.org)
using [mplbplot](https://github.com/pieterdavid/mplbplot).
"""

# The following lines set up the Jupyter notebook to show both the ROOT and matplotlib plots
# that are created "inline".
# 
# The ROOT, matplotlib.pyplot, and mplbplot modules are also loaded. The `mplbplot.decorateAxes`
# API is chosen here because it is more consistent with the (recommended) object-oriented matplotlib
# API, but alternatives are available
# (see [the mplbplot README](https://github.com/pieterdavid/mplbplot/blob/master/README.rst)).
#
# %jsroot on
# %matplotlib notebook
import ROOT
from matplotlib import pyplot as plt
import mplbplot.decorateAxes

# We will need `TH1F` objects to play with, e.g. a small sample drawn from a Gaussian distribution
h1 = ROOT.TH1F("aHisto", "", 20, -5., 5.)
h1.FillRandom("gaus", 250)

# The most basic way to draw a histogram is with a histogram line, which is done in ROOT as follows
# (see [THistPainter](https://root.cern.ch/doc/master/classTHistPainter.html) for documentation
# on styling such histogram plots; the `TCanvas::Draw` call is needed for the JupyROOT notebook)
cHIST = ROOT.TCanvas("cHIST")
h1.SetLineColor(ROOT.kBlue)
h1.Draw("HIST")
cHIST.Draw()

# The minimal code for doing the same in matplotlib using mplbplot is also very short
fig,ax = plt.subplots(num="HIST")
ax.rhist(h1, histtype="step", color="b")
# The `rhist` method mimics the
# [`Axes.hist`](http://matplotlib.org/api/_as_gen/matplotlib.axes.Axes.hist.html#matplotlib.axes.Axes.hist)
# method from matplotlib as closely as possible, but all arguments related to binning
# the dataset are not necessary in this case, since an exsiting histogram object is passed.
# `histtye="step"` is the matplotlib value that corresponds to `HIST` (the default is `bar`).
# 
# Another thing to note here is that the defaults for chosing the axis limits and tick frequency
# are quite different in matplotlib than in ROOT. Fortunately this is entirely customisable,
# see e.g. [the official examples](http://matplotlib.org/gallery.html#ticks_and_spines).
# The following method brings them closer to the ROOT default choices
def ticks_like_root(axes):
    import matplotlib.ticker
    axes.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=12, min_n_tickes=5))
    axes.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator())
    axes.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator())
#
fig,ax = plt.subplots(num="HIST2")
ax.rhist(h1, histtype="step", color="b")
ax.set_xlim(-5.,5.)
ticks_like_root(ax)

# Very often, histograms also have systematic uncertainties, or are scaled, so the uncertainty
# also needs to be displayed. A simple way to do this is by drawing a point with error bars
# for each bin (with the x-axis error bars usually indicating the bin width).
cE1P = ROOT.TCanvas("cE1P")
h1.SetLineColor(ROOT.kRed)
h1.SetMarkerColor(ROOT.kRed)
h1.SetMarkerStyle(ROOT.kFullCircle)
h1.Draw("P,E1")
cE1P.Draw()
#
fig,ax = plt.subplots(num="E1P")
ax.rerrorbar(h1, kind="bar", fmt="ro", mec="r")
ax.set_xlim(-5., 5.)
ax.set_ylim(ymin=0.)
ticks_like_root(ax)
# In addition to the options known from
# [`Axes.errorbar`](http://matplotlib.org/api/_as_gen/matplotlib.axes.Axes.errorbar.html#matplotlib.axes.Axes.errorbar),
# with the `kind="bar"` option, `rerrorbar` can also be used to draw error "boxes" (`E2`),
# with `kind='box'`, and error bands (`E3`), with `kind="band"`, e.g.
cE2H = ROOT.TCanvas("cE2H")
h1.SetMarkerStyle(0)
h1.SetLineColor(ROOT.kGreen)
h1.DrawCopy("HIST")
h1.SetFillColorAlpha(ROOT.kGreen, .3)
h1.Draw("E2,SAME")
cE2H.Draw()
#
fig,ax = plt.subplots(num="E2H")
ax.rhist(h1, histtype="step", color="g")
ax.rerrorbar(h1, kind="box", color="green", alpha=.3, lw=0)
ax.set_xlim(-5., 5.)
ax.set_ylim(ymin=0.)
ticks_like_root(ax)
