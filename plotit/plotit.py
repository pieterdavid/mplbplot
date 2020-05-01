from __future__ import absolute_import
"""
Python version of plotIt, for plotting with ROOT or matplotlib

Based on https://github.com/cp3-llbb/plotIt

WARNING: very much work-in-progress, many things are not implemented yet
"""
from future.utils import iteritems, itervalues
from builtins import range
from itertools import chain, islice
from functools import partial
import numbers
import numpy as np

from . import histo_utils as h1u
from . import logger

class lazyload(object):
    """
    Python2 equivalent of a read-only functools.cached_property

    On top of being available also for python before 3.8,
    having a separate class helps e.g. with optimisation
    (it is possible to identify all of these to group the loads,
    and clean up the objects).

    If the host class uses __slots__, the appropriate attribute
    must be defined there (name prefix with an underscore).
    """
    __slots__ = ("load", "_cName")
    def __init__(self, load):
        self.load = load
        self._cName = "_{0}".format(load.__name__)
    def __get__(self, instance, cls):
        value = getattr(instance, self._cName)
        if value is None:
            value = self.load(instance)
            setattr(instance, self._cName, value)
        return value

class File(object):
    """
    plotIt sample or file, since all plots for a sample are in one ROOT file.

    This object mainly holds the open TFile pointer, normalisation scale,
    and systematics dictionary for the sample. The configuration (from YAML)
    parameteres are collected in a :py:class:`plotit.config.File` instance,
    as the `cfg` attribute.
    """
    __slots__ = ("_tFile", "name", "path", "cfg", "scale", "systematics")
    def __init__(self, name, path, fCfg, config=None, systematics=None):
        self.name = name
        self.path = path
        self.cfg = fCfg
        self._tFile = None
        self.scale = File._getScale(self.cfg, config)
        self.systematics = dict((syst.name, syst) for syst in systematics if self.cfg.type != "DATA" and syst.on(self.name, self.cfg))
        logger.debug("Scale for file {0.name}: {0.scale:f}; systematics: {0.systematics!s}".format(self))
    @lazyload
    def tFile(self):
        from cppyy import gbl
        tf = gbl.TFile.Open(self.path)
        if not tf:
            logger.error("Could not open file {0}".format(self.path))
        return tf
    def getHist(self, plot, name=None):
        """ Get the histogram for the combination of ``plot`` and this file/sample """
        hk = FileHist(histoFile=self, plot=plot, name=name)
        from .systematics import SystVarsForHist
        hk.systVars = SystVarsForHist(hk, self.systematics)
        return hk
    @staticmethod
    def _getScale(fCfg, config):
        """ Infer the scale factor for histograms from the file dict and the overall config """
        if fCfg.type == "DATA":
            return 1.
        else:
            if fCfg.era:
                lumi = config["luminosity"][fCfg.era]
            elif isinstance(config["luminosity"], numbers.Number):
                lumi = config["luminosity"]
            else:
                lumi = sum(lumi for era,lumi in iteritems(config["luminosity"]))
            mcScale = ( lumi*fCfg.cross_section*fCfg.branching_ratio / fCfg.generated_events )
            if config.get("ignore-scales", False):
                return mcScale
            else:
                return mcScale*config.get("scale", 1.)*fCfg.scale
    def __repr__(self):
        return "File({0.path!r}, scale={0.scale}, systematics={0.systematics!r})".format(self)

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
        return GroupHist(self, [ f.getHist(plot) for f in self.files ])
    def __repr__(self):
        return "Group({0.name!r}, {0.files!r})".format(self)

class MemHist(object):
    """ In-memory histogram, minimally compatible with :py:class:`~plotit.plotit.FileHist` """
    def __init__(self, obj):
        self.obj = obj # the underlying object
    def contributions(self):
        yield self
    def __repr__(self):
        return "MemHist({0.obj!r})".format(self)

class FileHist(object):
    """
    Histogram from a file, or distribution for one sample.

    The actual object is only read into memory when first used.
    Transformations like scaling and rebinning are also applied then.
    In addition, references to the sample :py:class:`~plotit.plotit.File`
    and :py:class:`~plotit.config.Plot` are held.
    """
    __slots__ = ("_obj", "name", "_tFile", "plot", "hFile", "systVars")
    def __init__(self, name=None, tFile=None, plot=None, histoFile=None, systVars=None):
        """ Histogram key constructor. The object is read on first use, and cached.

        :param name:        name of the histogram inside the file (taken from ``plot`` if not specified)
        :param tFile:       ROOT file with histograms (taken from ``histoFile`` if not specified)
        :param plot:        :py:class:`~plotit.config.Plot` configuration
        :param histoFile:   :py:class:`plotit.plotit.File` instance corresponding to the sample
        """
        self._obj = None
        self.name = name if name else plot.name
        self._tFile = tFile ## can be explicitly passed, or None (taken from hFile on first use then)
        self.plot = plot
        self.hFile = histoFile
        self.systVars = systVars
    @lazyload
    def tFile(self): ## only called if not constructed explicitly
        return self.hFile.tFile
    def __str__(self):
        return 'FileHist("{0}", "{1}")'.format(self.tFile.GetName(), self.name)
    def clone(self, name=None, tFile=None, plot=None, histoFile=None, systVars=None):
        """ Modifying clone method. `systVars` is *not* included by default """
        return FileHist(name=(name if name is not None else self.name),
                        tFile=(tFile if tfile is not None else self.tFile),
                        plot=(plot if plot is not None else self.plot),
                        histoFile=(histoFile if histoFile is not None else self.histoFile),
                        systVars=systVars)
    @lazyload
    def obj(self):
        """ the underlying TH1 object """
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
        return res
    def getStyleOpt(self, name):
        return getattr(self.hFile.cfg, name)
    def contributions(self):
        yield self
    def __repr__(self):
        return "FileHist({0.name!r}, {0.hFile!r})".format(self)

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
    @lazyload
    def obj(self):
        """ the underlying TH1 object """
        res = h1u.cloneHist(self.entries[0].obj)
        for entry in islice(self.entries, 1, None):
            res.Add(entry.obj)
        return res
    def getStyleOpt(self, name):
        return getattr(self.group.cfg, name)
    def contributions(self):
        for contrib in self.entries:
            yield contrib

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
    __slots__ = ("entries", "_total", "_totalSystematics")
    def __init__(self, entries=None):
        self.entries = list(entries) if entries is not None else list()
        self._total = None
        self._totalSystematics = None
    def add(self, hist):
        """ Add a histogram to a stack """
        if self._total:
            raise RuntimeError("Stack has been built, no more entries should be added")
        self.entries.append(hist)
    def contributions(self):
        """ Iterate over contributions (histograms inside all entries) - for systematics calculation etc. """
        for entry in self.entries:
            for contrib in entry.contributions():
                yield contrib
    @lazyload
    def total(self):
        """ upper stack histogram """
        if not self.entries:
            raise RuntimeError("Cannot construct a stack without histogram entries")
        hSt = h1u.cloneHist(self.entries[0].obj)
        for nh in islice(self.entries, 1, None):
            hSt.Add(nh.obj)
        return hSt
    def allSystVarNames(self):
        """ Get the list of all systematics affecting the sum histogram """
        return set(chain.from_iterable(contrib.systVars for contrib in self.contributions()))
    def calcSystematics(self, systVarNames=None):
        """ Get the combined systematic uncertainty

        :param systVarNames:    systematic variations to consider (if None, all that are present are used for each histogram)
        """
        nBins = self.total.GetNbinsX()
        binRange = range(1,nBins+1) ## no overflow or underflow

        if systVarNames is None:
            systVarNames = self.allSystVarNames()

        ## TODO possible optimisations
        ## - build up the sum piece by piece (no dict then)
        ## - make entries the outer loop
        ## - calculate a systematic on the total if it applies to all entries and is parameterized
        systPerBin = dict((vn, np.zeros((nBins,))) for vn in systVarNames) ## including overflows
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

        return systInteg, totalSystInBins
    @lazyload
    def totalSystematics(self):
        """ (integral-total-systematic, array-of-bin-total-systematic-uncertainties) """
        return self.calcSystematics(systVarNames=None)
    def getTotalSystematics(self, systVarNames=None):
        if systVarNames is None:
            return self.totalSystematics
        else:
            return self.getTotalSystematics(systVarNames=systVarNames)
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

def loadHistograms(histograms):
    """
    Efficiently load all histograms from disk

    :param histograms: nominal histograms iterable. The systematic variations histograms are also found and loaded.
    """
    from .systematics import ShapeSystVar
    from collections import defaultdict
    h_per_file = defaultdict(list)
    for hk in histograms:
        if isinstance(hk, FileHist):
            h_per_file[hk.hFile.path].append(hk)
    nOKTot, nFailTot = 0, 0
    for fPath, fHKs in iteritems(h_per_file):
        nOK, nFail = 0, 0
        for hk in fHKs:
            if hk.obj is not None: ## trigger load
                nOK += 1
            else:
                nFail += 1
            if hk.systVars:
                for sv in itervalues(hk.systVars):
                    if isinstance(sv, ShapeSystVar.ForHist):
                        if sv.histUp.obj is not None:
                            nOK += 1
                        else:
                            nFail += 1
                        if sv.histDown.obj is not None:
                            nOK += 1
                        else:
                            nFail += 1
        logger.debug("Loaded {0:d} histograms from file {1} ({2:d} failed)".format(nOK, fPath, nFail))
        nOKTot += nOK
        nFailTot += nFail
    logger.debug("Loaded {0:d} histograms from {1:d} files ({2:d} failed)".format(nOKTot, len(h_per_file), nFailTot))

def clearHistograms(histograms):
    """
    Clear all histograms

    :param histograms: nominal histograms iterable. The systematic variations histograms are also found and loaded.
    """
    from .systematics import ShapeSystVar
    nCleared, nEmpty = 0, 0
    for hk in histograms:
        if isinstance(hk, FileHist):
            if hk._obj:
                del hk._obj
                nCleared += 1
            else:
                nEmpty += 1
            if hk.systVars:
                for sv in itervalues(hk.systVars):
                    if isinstance(sv, ShapeSystVar.ForHist):
                        if sv.histUp._obj:
                            del sv.histUp._obj
                            nCleared += 1
                        else:
                            nEmpty += 1
                        if sv.histDown._obj:
                            del sv.histDown._obj
                            nCleared += 1
                        else:
                            nEmpty += 1
    logger.debug("Cleared {0:d} histograms from memory ({1:d} were not loaded)".format(nCleared, nEmpty))

def makeStackRatioPlots(plots, samples, systematics=None, config=None, outdir=".", backend="matplotlib", chunkSize=100):
    """
    Draw a traditional plotIt plot: data and MC stack, with (optional) signal distributions and ratio below

    :param plots: list of plots to draw
    :param samples: samples (groups and files) to consider
    :param systematics: selected systematics (TODO: implement this)
    :param config: global config (TODO is this necessary, or can it all be put in the plot config?)
    :param outdir: output directory
    :param backend: backend (ROOT or matplotlib)
    """
    ## default kwargs
    if backend == "matplotlib":
        from .draw_mpl import drawStackRatioPlot
    elif backend == "ROOT":
        from .draw_root import drawStackRatioPlot
    else:
        raise ValueError("Unknown backend: {0!r}, valid choices are 'ROOT' and 'matplotlib'".format(backend))

    dataSamples = [ smp for smp in samples if smp.cfg.type == "DATA" ]
    mcSamples = [ smp for smp in samples if smp.cfg.type == "MC" ]
    signalSamples = [ smp for smp in samples if smp.cfg.type == "SIGNAL" ]

    ## build stacks
    stacks_per_plot = [ (plot, (
                Stack(entries=[smp.getHist(plot) for smp in dataSamples]),
                Stack(entries=[smp.getHist(plot) for smp in mcSamples]),
                [ smp.getHist(plot) for smp in signalSamples ]
                )) for plot in itervalues(plots) ]
    logger.debug("Drawing {0:d} plots, splitting in chunks of {1:d}".format(len(plots), chunkSize))
    ## load and draw, in chunks
    for i in range(0, len(stacks_per_plot), chunkSize):
        i_stacks_plots = stacks_per_plot[i:i+chunkSize]
        loadHistograms(chain.from_iterable(
            chain(dataStack.contributions(), mcStack.contributions(), sigHists)
            for plot, (dataStack, mcStack, sigHists) in i_stacks_plots))
        for plot, (dataStack, mcStack, sigHists) in i_stacks_plots:
            logger.debug("Drawing plot {0}".format(plot.name))
            drawStackRatioPlot(plot, mcStack, dataStack, outdir=outdir)
        clearHistograms(chain.from_iterable(
            chain(dataStack.contributions(), mcStack.contributions(), sigHists)
            for plot, (dataStack, mcStack, sigHists) in i_stacks_plots))

def getHistoPath(histoPath, cfgRoot=".", baseDir="."):
    import os.path
    if os.path.isabs(histoPath):
        return histoPath
    elif os.path.isabs(cfgRoot):
        return os.path.join(cfgRoot, histoPath)
    else:
        return os.path.join(baseDir, cfgRoot, histoPath)

def samplesFromFilesAndGroups(allFiles, groupConfigs, eras=None):
    """ Group and sort files that should be included for a era (or a set of eras) """
    from collections import defaultdict
    files_by_group = defaultdict(list)
    groups_and_samples = []
    for fl in allFiles:
        if eras is None or fl.cfg.era is None or fl.cfg.era in eras:
            if fl.cfg.group and fl.cfg.group in groupConfigs:
                files_by_group[fl.cfg.group].append(fl)
            else:
                if fl.cfg.group:
                    logger.warning("Group {0.cfg.group!r} of sample {0.name!r} not found, adding ungrouped".format(fl))
                groups_and_samples.append(fl)
    groups_and_samples += [ Group(gNm, files_by_group[gNm], gCfg)
            for gNm, gCfg in groupConfigs.items() if gNm in files_by_group ]
    return sorted(groups_and_samples, key=lambda f : f.cfg.order if f.cfg.order is not None else 0, reverse=True)

def samplesForEras(samples, eras=None):
    """ Reduce a list of samples (files and groups) to those that should be included for a specific era (or a set of eras) """
    if isinstance(eras, str):
        eras = [eras]
    selSamples = []
    for smp in samples:
        if eras is None:
            selSamples.append(smp)
        elif isinstance(smp, File):
            if smp.era is None or smp.era in eras:
                selSamples.append(smp)
        elif isinstance(smp, Group):
            eraFiles = [ f for f in smp.files if f.era is None or f.era in eras ]
            if eraEntries:
                selSamples.append(Group(smp.name, eraFiles, smp.cfg))
    return selSamples

def loadFromYAML(yamlFileName, histodir=".", eras=None, vetoFileAttributes=None):
    """
    Parse a plotIt YAML file

    :param yamlFileName: config file path
    :param histodir: base path for finding histograms (to be combined with ``'root'`` in configuration and the sample file names)
    :param eras: selected era, or list of selected eras (default: all that are present)
    :param vetoFileAttributes: names of file attributes to remove (TODO: to be removed - vetoing can be done when generating plots.yml)
    """
    from .config import load as load_plotIt_YAML
    config, fileCfgs, groupCfgs, plots, systematics = load_plotIt_YAML(yamlFileName, vetoFileAttributes=vetoFileAttributes)
    resolve = partial(getHistoPath, cfgRoot=config["root"], baseDir=histodir)
    samples = samplesFromFilesAndGroups(
            [ File(fNm, resolve(fNm), fCfg, config=config, systematics=systematics) for fNm, fCfg in fileCfgs.items() ],
            groupCfgs, eras=(eras if eras is not None else config.get("eras")))
    return config, samples, plots, systematics

def plotItFromYAML(yamlFileName, histodir=".", outdir=".", eras=None, vetoFileAttributes=None, backend="matplotlib"):
    logger.info("Running like plotIt with config {0}, histodir={1}, outdir={1}".format(yamlFileName, histodir, outdir))
    config, samples, plots, systematics = loadFromYAML(yamlFileName, histodir=histodir, eras=eras, vetoFileAttributes=vetoFileAttributes)
    makeStackRatioPlots(plots, samples, systematics=systematics, config=config, outdir=outdir, backend=backend)

def makeBaseArgsParser(description=None):
    def optStrList(value):
        if value:
            return value.split(",")
    import argparse
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("yamlFile", help="plotIt configuration file (e.g. plots.yml)")
    parser.add_argument("--histodir", help="base path for finding histograms (to be combined with ``'root'`` in configuration and the sample file names; default: the directory that contains yamlFile)")
    parser.add_argument("--eras", type=optStrList, help="Era or (comma-separated) list of eras to consider")
    parser.add_argument("--vetoFileAttributes", type=optStrList, help="Comma-separated list of file attributes to remove from the config file")
    return parser

def inspectConfig():
    parser = makeBaseArgsParser(description="Load and interactively inspect a plotIt config")
    args = parser.parse_args()
    import os.path
    if args.histodir:
        histodir = args.histodir
    else:
        histodir = os.path.dirname(args.yamlFile)
    config, samples, plots, systematics = loadFromYAML(args.yamlFile, histodir=histodir, eras=args.eras, vetoFileAttributes=args.vetoFileAttributes)
    import IPython
    IPython.embed()

def plotIt_cli():
    parser = makeBaseArgsParser(description="Python implementation of the plotIt executable (not fully compatible)" )
    parser.add_argument("--outdir", "-o", default=".", help="Output directory")
    parser.add_argument("--backend", default="matplotlib", choices=["ROOT", "matplotlib"], help="Backend")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    import os.path
    if args.histodir:
        histodir = args.histodir
    else:
        histodir = os.path.dirname(args.yamlFile)
    import logging
    logging.basicConfig(level=(logging.DEBUG if args.verbose else logging.INFO))
    plotItFromYAML(args.yamlFile, histodir=histodir, outdir=args.outdir, eras=args.eras, vetoFileAttributes=args.vetoFileAttributes, backend=args.backend)
