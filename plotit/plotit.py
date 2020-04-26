from __future__ import absolute_import
"""
Python version of plotIt, for plotting with ROOT or matplotlib

Based on https://github.com/cp3-llbb/plotIt

WARNING: very much work-in-progress, many things are not implemented yet
"""
from future.utils import iteritems, itervalues
from builtins import range
from itertools import chain, islice
import numpy as np

from . import config
from . import histo_utils as h1u
from .systematics import SystVarsForHist
from . import logger

class File(object):
    """
    plotIt sample or file, since all plots for a sample are in one ROOT file.

    This object mainly holds the open TFile pointer, normalisation scale,
    and systematics dictionary for the sample. The configuration (from YAML)
    parameteres are collected in a :py:class:`plotit.config.File` instance,
    as the `cfg` attribute.
    """
    __slots__ = ("_tf", "name", "path", "cfg", "scale", "systematics")
    def __init__(self, name, path, fCfg, config=None, systematics=None):
        self.name = name
        self.path = path
        self.cfg = fCfg
        from cppyy import gbl
        self._tf = gbl.TFile.Open(self.path)
        self.scale = File._getScale(self.cfg, config)
        self.systematics = dict((syst.name, syst) for syst in systematics if self.cfg.type != "data" and syst.on(self.name, self.cfg))
        logger.debug("Scale for file {0.name}: {0.scale:f}; systematics: {0.systematics!s}".format(self))
    def getHist(self, plot, name=None):
        """ Get the histogram for the combination of ``plot`` and this file/sample """
        hk = FileHist(histoFile=self, plot=plot, name=name)
        hk.systVars = SystVarsForHist(hk, self.systematics)
        return hk
    @staticmethod
    def _getScale(fCfg, config):
        """ Infer the scale factor for histograms from the file dict and the overall config """
        if fCfg.type == "data":
            return 1.
        else:
            if fCfg.era:
                lumi = config["eras"][fCfg.era]["luminosity"]
            else:
                lumi = config["luminosity"]
            mcScale = ( lumi*fCfg.cross_section*fCfg.branching_ratio / fCfg.generated_events )
            if config.get("ignore-scales", False):
                return mcScale
            else:
                return mcScale*config.get("scale", 1.)*fCfg.scale

class Group(object):
    """ Group of samples

    Similar interface as :py:class:`~plotit.plotit.File`, based on a list of those.
    """
    __slots__ = ("name", "files", "cfg")
    def __init__(self, name, files, gCfg):
        self.name = name
        self.cfg = gCfg
        self.files = files
    def getHist(self, plot):
        """ Get the histogram for the combination of ``plot`` and this group of samples """
        return GroupHist(self, [ f.getHist(plot) for f in files ])

def getFileOrder(hFile, groups=None):
    if hFile.order:
        return hFile.order
    elif groups and hFile.group in groups:
        return groups[hFile.group].order
    return 0

class MemHist(object):
    """ In-memory histogram, minimally compatible with :py:class:`~plotit.plotit.FileHist` """
    def __init__(self, obj):
        self.obj = obj # the underlying object
    def contributions(self):
        yield self

class FileHist(object):
    """
    Histogram from a file, or distribution for one sample.

    The actual object is only read into memory when first used.
    Transformations like scaling and rebinning are also applied then.
    In addition, references to the sample :py:class:`~plotit.plotit.File`
    and :py:class:`~plotit.config.Plot` are held.
    """
    __slots__ = ("_obj", "name", "tFile", "plot", "hFile", "systVars")
    def __init__(self, name=None, tFile=None, plot=None, histoFile=None, systVars=None):
        """ Histogram key constructor. The object is read on first use, and cached.

        :param name:        name of the histogram inside the file (taken from ``plot`` if not specified)
        :param tFile:       ROOT file with histograms (taken from ``histoFile`` if not specified)
        :param plot:        :py:class:`~plotit.config.Plot` configuration
        :param histoFile:   :py:class:`plotit.plotit.File` instance corresponding to the sample
        """
        self._obj = None
        self.name = name if name else plot.name
        self.tFile = tFile if tFile else histoFile._tf
        self.plot = plot
        self.hFile = histoFile
        self.systVars = systVars
    def __str__(self):
        return 'FileHist("{0}", "{1}")'.format(self.tFile.GetName(), self.name)
    def clone(self, name=None, tFile=None, plot=None, histoFile=None, systVars=None):
        """ Modifying clone method. `systVars` is *not* included by default """
        return FileHist(name=(name if name is not None else self.name),
                        tFile=(tFile if tfile is not None else self.tFile),
                        plot=(plot if plot is not None else self.plot),
                        histoFile=(histoFile if histoFile is not None else self.histoFile),
                        systVars=systVars)
    def _get(self):
        ## load the object from the file, and apply transformations as needed
        if ( not self.tFile ) or self.tFile.IsZombie() or ( not self.tFile.IsOpen() ):
            raise RuntimeError("File '{}'cannot be read".format(self.tFile))
        res = self.tFile.Get(self.name)
        if not res:
            raise KeyError("Could not retrieve key '{0}' from file {1!r}".format(self.name, self.tFile))
        ## scale/rebin/crop if needed
        scale = self.hFile.scale
        rebin = self.plot.rebin
        xOverflowRange = self.plot.x_axis_range
        if ( scale != 1. ) or ( rebin != 1 ) or ( xOverflowRange is not None ):
            res = h1u.cloneHist(res)
            if xOverflowRange is not None:
                res.GetXaxis().SetRangeUser(xOverflowRange[0], xOverflowRange[1])
                from .histo_utils import addOverflow
                addOverflow(res, res.GetXaxis().GetFirst(), True )
                addOverflow(res, res.GetXaxis().GetLast() , False)
            if scale != 1.:
                if not res.GetSumw2():
                    res.Sumw2()
                res.Scale(scale)
            if rebin != 1:
                res.Rebin(rebin)
        ##
        self._obj = res
    @property
    def obj(self):
        """ the underlying TH1 object """
        if not self._obj:
            self._get()
        return self._obj
    def getStyleOpt(self, name):
        return getattr(self.hFile.cfg, name)
    def contributions(self):
        yield self

class GroupHist(object):
    """
    Combined histogram for a group of samples.

    The public interface is almost identical to :py:class:`~plotit.plotit.FileHist`
    """
    __slots__ = ("_obj", "entries", "group")
    def __init__(self, group, entries):
        """ Constructor

        :param group: :py:class:`~plotit.plotit.Group` instance
        :param entries: a :py:lass:`~plotit.plotit.FileHist` for each sample in the group
        """
        self._obj = None
        self.group = group
        self.entries = entries
        ## TODO is self.plot needed? explicitly or as property
    def _get(self):
        res = h1u.cloneHist(sef.entries[0].hist.obj)
        for entry in islice(self.entries, 1, None):
            res.Add(entry.hist.obj)
        self._obj = res
    @property
    def obj(self):
        """ the underlying TH1 object """
        if not self._obj:
            self._get()
        return self._obj
    def getStyleOpt(self, name):
        return getattr(self.group.cfg, name)
    def contributions(self):
        yield from entries

class Stack(object):
    """
    Stack of distribution contributions from different samples.

    The entries are instances of either :py:class:`~plotit.plotit.FileHist` or
    :py:class:`~plotit.plotit.GroupHist`, for a single sample or a group of them,
    respectively.
    In addition to summing the histograms, helper methods to calculate the
    systematic uncertainty on the total, combined with the statistical uncertainty
    or not, are provided.
    """
    def __init__(self):
        self.entries = [] # list of histograms (entries) used to build the stack
        self._total = None ## sum histogram (lazy, constructed when accessed and cached)
        self._totalSystAll = None
    def add(self, hist):
        """ Add a histogram to a stack """
        if self._total:
            raise RuntimeError("Stack has been built, no more entries should be added")
        self.entries.append(hist)
    def contributions(self):
        """ Iterate over contributions (histograms inside all entries) - for systematics calculation etc. """
        for entry in self.entries:
            yield from entry.contributions()
    def _get(self):
        hSt = h1u.cloneHist(self.entries[0].obj)
        for nh in islice(self.entries, 1, None):
            hSt.Add(nh.obj)
        self._total = hSt
    @property
    def total(self):
        """ upper stack histogram """
        if ( not self._total ) and self.entries:
            self._get()
        return self._total
    def allSystVarNames(self):
        """ Get the list of all systematics affecting the sum histogram """
        return set(chain.from_iterable(contrib.systVars for contrib in self.contributions()))
    def _calcSystematics(self, systVarNames=None):
        """ Get the combined systematic uncertainty

        :param systVarNames:    systematic variations to consider (if None, all that are present are used for each histogram)
        """
        nBins = self.total.GetNbinsX()
        binRange = range(1,nBins+1) ## no overflow or underflow

        if systVarNames is not None:
            systVars = systVarNames
        else:
            systVars = self.allSystVarNames()

        ## TODO possible optimisations
        ## - build up the sum piece by piece (no dict then)
        ## - make entries the outer loop
        ## - calculate a systematic on the total if it applies to all entries and is parameterized
        systPerBin = dict((vn, np.zeros((nBins,))) for vn in systVars) ## including overflows
        maxVarPerBin = np.zeros((nBins,)) ## helper object - reduce allocations
        systInteg = 0. ## TODO FIXME
        for systN, systInBins in iteritems(systPerBin):
            for contrib in self.contributions():
                syst = contrib.systVars.get(systN)
                if syst is not None:
                    for i in iter(binRange):
                        maxVarPerBin[i-1] = max(abs(syst.up(i)-syst.nom(i)), abs(syst.down(i)-syst.nom(i)))
                    systInBins += maxVarPerBin
                    systInteg += np.sum(maxVarPerBin)

        totalSystInBins = np.sqrt(sum( binSysts**2 for binSysts in itervalues(systPerBin) ))
        if len(systPerBin) == 0: ## no-syst case
            totalSystInBins = np.zeros((nBins,))

        if systVarNames is None:
            self._totalSystAll = systInteg, totalSystInBins

        return systInteg, totalSystInBins
    def getTotalSystematics(self, systVarNames=None):
        if systVarNames is not None:
            return self._calcSystematics(systVarNames=systVarNames)
        else:
            if self._totalSystAll is None:
                self._calcSystematics()
            return self._totalSystAll
    def getSystematicHisto(self, systVarNames=None):
        """ construct a histogram of the stack total, with only systematic uncertainties """
        __, totalSystInBins = self.getTotalSystematics(systVarNames=systVarNames)
        return h1u.histoWithErrors(self.total, totalSystInBins)
    def getStatSystHisto(self, systVarNames=None):
        """ construct a histogram of the stack total, with statistical+systematic uncertainties """
        __, totalSystInBins = self.getTotalSystematics(systVarNames=systVarNames)
        return h1u.histoWithErrorsQuadAdded(self.total, totalSystInBins)
    def getRelSystematicHisto(self, systVarNames=None):
        """ construct a histogram of the relative systematic uncertainties for the stack total """
        return h1u.histoDivByValues(self.getSystematicHisto(systVarNames))

    @staticmethod
    def merge(*stacks):
        """ Merge two or more stacks """
        if len(stacks) < 2:
            return stacks[0]
        else:
            from .systematics import MemHist
            mergedSt = Stack()
            for i,entry in enumerate(stacks[0].entries):
                newHist = h1u.cloneHist(entry.obj)
                for stck in islice(stacks, 1, None):
                    newHist.Add(stck.entries[i].obj)
                mergedSt.add(MemHist(newHist), systVars=entry.systVars)
            return mergedSt

def drawPlot(plot, expStack, obsStack, outdir="."):
    from .histstacksandratioplot import THistogramRatioPlot
    theplot = THistogramRatioPlot(expected=expStack, observed=obsStack) ## TODO more opts?
    theplot.draw()
    #
    if plot.x_axis_range:
        theplot.ax.set_xlim(*plot.x_axis_range)
    if plot.x_axis:
        theplot.rax.set_xlabel(plot.x_axis)
    #
    if plot.y_axis_range:
        theplot.ax.set_ylim(*plot.y_axis_range)
    else:
        if not plot.log_y:
            theplot.ax.set_ylim(0.)
    if plot.y_axis:
        theplot.ax.set_ylabel(plot.y_axis)
    elif plot.y_axis_format:
        pass
    #
    import os.path
    for ext in plot.save_extensions:
        theplot.fig.savefig(os.path.join(outdir, "{0}.{1}".format(plot.name, ext)))

def plotIt(plots, files, groups=None, systematics=None, config=None, outdir="."):
    ## default kwargs
    if systematics is None:
        systematics = list()
    if config is None:
        config = dict()

    for pName, aPlot in iteritems(plots):
        obsStack = Stack()
        expStack = Stack()
        for f in files:
            hk = f.getHist(aPlot)
            if f.cfg.type == "data":
                obsStack.add(hk)
            elif f.cfg.type == "mc":
                expStack.add(hk)

        drawPlot(aPlot, expStack, obsStack, outdir=outdir)

def _plotIt_histoPath(histoPath, cfgRoot, baseDir):
    import os.path
    if os.path.isabs(histoPath):
        return histoPath
    elif os.path.isabs(cfgRoot):
        return os.path.join(cfgRoot, histoPath)
    else:
        return os.path.join(baseDir, cfgRoot, histoPath)

def plotItFromYAML(yamlFileName, histodir=".", outdir="."):
    from .config import load as load_plotIt_YAML
    logger.info("Running like plotIt with config {0}, histodir={1}, outdir={1}".format(yamlFileName, histodir, outdir))
    config, fileCfgs, groupCfgs, plots, systematics = load_plotIt_YAML(yamlFileName, histodir=histodir)
    files = sorted([ File(fNm, _plotIt_histoPath(fNm, config["root"], histodir),
                          fCfg, config=config, systematics=systematics)
                    for fNm, fCfg in fileCfgs.items() ],
                    key=lambda f : getFileOrder(f.cfg, groupCfgs), reverse=True)
    ### get list of files, get list of systs, dict of systs per file; then list of plots: for each plot build the stacks and draw
    ## TODO cfg -> config
    plotIt(plots, files, groups=groupCfgs, systematics=systematics, config=config, outdir=outdir)

if __name__ == "__main__": ## quick test of basic functionality
    import ROOT
    ROOT.PyConfig.IgnoreCommandLineOptions = True
    import os.path
    my_plotit_dir = "" ## FIXME
    plotItFromYAML(os.path.join(my_plotit_dir, "examples/example.yml"))
    from matplotlib import pyplot as plt
    plt.show()
