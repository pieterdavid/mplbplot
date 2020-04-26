from __future__ import absolute_import
"""
Helper objects for plots with several stacks (e.g. data and and simulation)

WARNING: work in progress, some things are not implemented yet
"""

from builtins import zip, range
from future.utils import iteritems

from . import histo_utils as h1u
from .plotit import Stack

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

        self.expected = expected if expected is not None else Stack()
        self.observed = observed if observed is not None else Stack()
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
        exp_hists, exp_colors = zip(*((eh.obj, eh.getStyleOpt("fill_color")) for eh in self.expected.entries))
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
