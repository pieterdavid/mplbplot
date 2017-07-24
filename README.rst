mplbplot
========

Simple and customizable plotting of ROOT objects (TH1, TH2, TGraph...)
with matplotlib.

`matplotlib <http://matplotlib.org>`_ is a powerful Python plotting
library.
This package aims to provide a simple way to use histograms and graphs
created with the `ROOT <https://root.cern.ch>`_ framework,
that is ubiquitous in experimental high-energy physics,
in matplotlib.
The wrapper methods rely on the PyROOT bindings and are kept minimal,
in order to give the user maximal flexibility to control the layout.

A simple example:

.. code:: python

    import ROOT
    h1 = ROOT.TH1F("h1", "h1", 20, -5., 5.)
    h1.FillRandom("gaus", 250)

    ## draw with ROOT
    c1 = ROOT.TCanvas("c1")
    h1.GetXaxis().SetRangeUser(-5., 5.)
    h1.SetLineColor(ROOT.kRed)
    h1.Draw("HIST")
    c1.Update()

    ## draw with mplbplot
    import matplotlib.pyplot as plt
    import mplbplot.decorateAxes ## object-oriented API

    fig,ax = plt.subplots(num="Fig1")
    ax.rhist(h1, histtype="step", color="r")
    ax.set_xlim(-5., 5.)
    plt.show()

More usage examples can be found in `the examples directory
<https://github.com/pieterdavid/mplbplot/blob/master/examples>`_.
A more diverse set of plots made with the help of this package
can be found in `my PhD thesis <http://inspirehep.net/record/1492009>`_.

Three different ways for importing the helper methods can be used
(they can be freely mixed as well): the first blends nicely with
matplotlib's object-oriented API, and adds ``rhist``, ``rplot``, etc.
methods to ``matplotlib.axes.Axes`` when importing ``mplbplot.decorateAxes``, e.g.

.. code:: python

    import ROOT
    h = ROOT.TH1F("h1", "h1", 10, -5., 5.)
    h.FillRandom("gaus", 1000)

    from matplotlib import pyplot as plt
    import mplbplot.decorateAxes ## object-oriented API

    fig,ax = plt.subplots()
    ax.rhist(h, histtype="step", color="r")

The second adds the equivalent methods to the ``matplotlib.pyplot`` module, e.g.

.. code:: python

    import ROOT
    h = ROOT.TH1F("h1", "h1", 10, -5., 5.)
    h.FillRandom("gaus", 1000)

    from matplotlib import pyplot as plt
    import mplbplot.decoratePyplot ## pyplot decorators

    fig,ax = plt.subplots()
    plt.rhist(h, histtype="step", color="b")

The ``mplbplot.pyplot`` module provides wrapper methods that check
if the first argument is a ROOT object, take the custom implementation
in that case, or fall back to the corresponding ``matplotlib.pyplot``
method otherwise, the example can then be written as

.. code:: python

    import ROOT
    h = ROOT.TH1F("h1", "h1", 10, -5., 5.)
    h.FillRandom("gaus", 1000)

    from matplotlib.pyplot import *
    from mplbplot.pyplot import *

    fig,ax = subplots()
    hist(h, histtype="step", color="g")


Code overview
-------------
The code is structured in two layers:
a set of decorators for pythonic access to the contents of ROOT
histograms and graphs,
and drawing methods that mimic those in matplotlib's
`pyplot <http://matplotlib.org/api/pyplot_summary.html>`_ and
`axes <http://matplotlib.org/api/axes_api.html>`_ modules,
but take a ROOT histogram or graph as their first argument.

The decorators are a ``bins`` method for histograms,
and a ``points`` method for graphs, both returning a list-like object,
with each element referring to a histogram bin or graph point.
Accessing the attributes of the (proxy) bin or points objects
will call the corresponding accessor of the histogram object,
e.g. ``bins(h)[1].content`` is equivalent to ``h.GetBinContent(1)``,
and ``points(g)[0].x`` to ``g.GetX()[0]``.

This turns out to be quite covenient when writing the drawing methods,
where several bin or point properties
(e.g. bin center, width, and height,
or point coordinates and uncertainties)
are often iterated over together, in ``zip`` mode.

The helper methods can be accessed in three ways, depending on the
matplotlib API choice, and the preference for making the difference
between the ``matplotlib`` and ``mplbplot`` methods explicit or not.
See above for an example of each.


Finally, the ``mplbplot.plothelpers`` module contains a collection of
components (tick label formatters etc.) and methods that may be useful
for providing a uniform layout similar to the default ROOT style.
