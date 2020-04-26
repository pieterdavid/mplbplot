from __future__ import absolute_import
"""
Helper objects for plots with several stacks (e.g. data and and simulation)

WARNING: work in progress, some things are not implemented yet
"""

import numpy as np
from builtins import zip, range
from future.utils import iteritems, itervalues
from itertools import chain

from . import histo_utils as h1u

class THistogramStack(object):
    """
    Python equivalent of THStack

    For the simplest cases, calling `matplotlib.axes.hist` with list arguments works,
    but for automatic calculation of statistical/systematic/combined uncertainties
    on the total, and ratios between stacks, a container object is helpful
    """
    class Entry(object):
        """ THistogramStack helper class: everything related to one histogram in the stack """
        def __init__(self, hist, label=None, systVars=None):
            self.hist = hist
            self.label = label
            self.systVars = systVars if systVars else dict() ## NOTE this can be an actual dictionary, or a small object that knows how to retrieve the variations from the file, as long as systVars[systName].up and systVars[systName].down do what is expected

    def __init__(self):
        self.entries = [] # list of histograms (entries) used to build the stack
        self._total = None ## sum histograms (lazy, constructed when accessed and cached)

    def add(self, hist, **kwargs):
        """ Main method: add a histogram on top of the stack """
        if self._total:
            raise RuntimeError("Stack has been built, no more entries should be added")
        self.entries.append(THistogramStack.Entry(hist, **kwargs))

    @property
    def total(self):
        """ upper stack histogram """
        if ( not self._total ) and self.entries:
            hSt = h1u.cloneHist(self.entries[0].hist.obj)
            for nh in self.entries[1:]:
                hSt.Add(nh.hist.obj)
            self._total = hSt
        return self._total

    @staticmethod
    def merge(*stacks):
        """ Merge two or more stacks """
        if len(stacks) < 2:
            return stacks[0]
        else:
            from .systematics import MemHistoKey
            mergedSt = THistogramStack()
            for i,entry in enumerate(stacks[0].entries):
                newHist = h1u.cloneHist(entry.hist.obj)
                for stck in stacks[1:]:
                    newHist.Add(stck.entries[i].hist.obj)
                mergedSt.add(MemHistoKey(newHist), label=entry.label, systVars=entry.systVars)
            return mergedSt

    def _defaultSystVarNames(self):
        """ Get the combined (total rate and per-bin) systematics

        systVarNames: systematic variations to consider (if None, all that are present are used for each histogram)
        """
        return set(chain.from_iterable(contrib.systVars for contrib in self.entries))

    def getTotalSystematics(self, systVarNames=None):
        """ Get the combined systematics

        systVarNames: systematic variations to consider (if None, all that are present are used for each histogram)
        """
        nBins = self.total.GetNbinsX()
        binRange = range(1,nBins+1) ## no overflow or underflow

        if systVarNames is None:
            systVarNames = self._defaultSystVarNames()

        systPerBin = dict((vn, np.zeros((nBins,))) for vn in systVarNames) ## including overflows
        systInteg = 0. ## TODO FIXME
        for systN, systInBins in iteritems(systPerBin):
            for contrib in self.entries:
                syst = contrib.systVars.get(systN)
                if syst is not None:
                    maxVarPerBin = np.array([ max(abs(syst.up(i)-syst.nom(i)), abs(syst.down(i)-syst.nom(i))) for i in iter(binRange) ])
                    systInBins += maxVarPerBin
                    systInteg += np.sum(maxVarPerBin)

        totalSystInBins = np.sqrt(sum( binSysts**2 for binSysts in itervalues(systPerBin) ))
        if len(systPerBin) == 0: ## no-syst case
            totalSystInBins = np.zeros((nBins,))

        return systInteg, totalSystInBins

    def getSystematicHisto(self, systVarNames=None):
        """ construct a histogram of the stack total, with only systematic uncertainties """
        systInteg, totalSystInBins = self.getTotalSystematics(systVarNames=systVarNames)
        return h1u.histoWithErrors(self.total, totalSystInBins)
    def getStatSystHisto(self, systVarNames=None):
        """ construct a histogram of the stack total, with statistical+systematic uncertainties """
        systInteg, totalSystInBins = self.getTotalSystematics(systVarNames=systVarNames)
        return h1u.histoWithErrorsQuadAdded(self.total, totalSystInBins)
    def getRelSystematicHisto(self, systVarNames=None):
        """ construct a histogram of the relative systematic uncertainties for the stack total """
        return h1u.histoDivByValues(self.getSystematicHisto(systVarNames))


class THistogramRatioPlot(object):
    """
    Helper class for the common use case of a pad with two histogram stacks (MC and data or, more generally, expected and observed) and their ratio in a smaller pad below
    """
    def __init__(self, expected=None, observed=None, other=None): ## FIXME more (for placement of the axes)
        ## TODO put placement in some kind of helper method (e.g. a staticmethod that takes the fig)
        import matplotlib.pyplot as plt
        import matplotlib.ticker
        import mplbplot.decorateAxes ## axes decorators for TH1F
        from mplbplot.plothelpers import formatAxes, minorTicksOn

        self.fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios":(4,1)}, figsize=(7.875, 7.63875)) ## ...
        self.ax, self.rax = tuple(axes)
        self.rax.set_ylim(.5, 1.5)
        self.rax.set_ylabel("Data / MC")
        self.rax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(.2))
        formatAxes(self.ax)
        formatAxes(self.rax, axis="x")
        minorTicksOn(self.rax.yaxis)

        #self.ax  = fig.add_axes((.17, .30, .8, .65), adjustable="box-forced", xlabel="", xticklabels=[]) ## left, bottom, width, height
        #self.rax = fig.add_axes((.17, .13, .8, .15), adjustable="box-forced")

        self.expected = expected if expected is not None else THistogramStack()
        self.observed = observed if observed is not None else THistogramStack()
        self.other = other if other is not None else dict() ## third category: stacks that are just overlaid but don't take part in the ratio
    def __getitem__(self, ky):
        return self.other[ky]

    def draw(self):### TODO add opts
        self.drawDistribs(self.ax)
        self.drawRatio(self.rax)

    def drawDistribs(self, ax=None):
        """ Draw distributions on an axes object (by default the main axes associated to this plot) """
        if ax is None:
            ax = self.ax

        ## expected
        exp_hists, exp_colors = zip(*((eh.hist.obj, eh.hist.getStyleOpt("fill_color")) for eh in self.expected.entries))
        ax.rhist(exp_hists, histtype="stepfilled", color=exp_colors, stacked=True)
        exp_statsyst = self.expected.getStatSystHisto()
        ax.rerrorbar(exp_statsyst, kind="box", hatch=8*"/", ec="none", fc="none")
        ## observed
        ax.rerrorbar(self.observed.total, kind="bar", fmt="ko")

    def drawRatio(self, ax=None):
        if ax is None:
            ax = self.rax

        ax.axhline(1., color="k") ## should be made optional, and take options for style (or use the grid settings)

        rx,ry,ryerr = h1u.divide(self.observed.total, self.expected.total)
        ax.errorbar(rx, ry, yerr=ryerr, fmt="ko")

        ## then systematics...
        exp_syst_rel = self.expected.getRelSystematicHisto()
        ax.rerrorbar(exp_syst_rel, kind="box", hatch=8*"/", ec="none", fc="none")
