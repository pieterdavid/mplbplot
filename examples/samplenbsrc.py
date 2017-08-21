"""
This is an example of a python module that is written to be both
a set of tests and a jupyter notebook source,
reusing the tests as API usage examples.
"""

# let's start with something simple: making sure we will see all graphics inline

# (the nice thing, btw, is that an empty line will split a text block, and an empty comment a code block
# --- but if they are attached, they are kept together. An empty line will *not* split a code block, though
# % jsroot on
#
# % matplotlib inline

# and also the imports that we'll need to use ROOT, matplotlib, and the helper scripts
import ROOT

import matplotlib.pyplot as plt
import mplbplot.decorateAxes

# Next, let's construct a simple ROOT histogram to play with
h1 = ROOT.TH1F("h1", "", 10, -5., 5.)
h1.FillRandom("gaus", 250)

# First plot it simply like a histogram with ROOT
c1 = ROOT.TCanvas("c1")
h1.Draw("HIST")
c1.Draw()
# Next, same thing with mplbplot
fig,ax = plt.subplots(num="c1")
ax.rhist(h1, color="k")
# THE END for now
