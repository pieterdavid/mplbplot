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

class lazyload(property):
    """
    Python2 equivalent of a read-only functools.cached_property

    On top of being available also for python before 3.8,
    having a separate class helps e.g. with optimisation
    (it is possible to identify all of these to group the loads,
    and clean up the objects).

    If the host class uses __slots__, the appropriate attribute
    must be defined there (name prefix with an underscore), and
    initialized (usually to ``None``) in the constructor.
    """
    __slots__ = ("_cName",)
    def __init__(self, fget=None):
        super(lazyload, self).__init__(fget=fget, doc=property.__doc__)
        self._cName = "_{0}".format(fget.__name__)
    def __get__(self, instance, cls):
        value = getattr(instance, self._cName)
        if value is None:
            value = self.fget(instance)
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
        logger.debug("Scale for file {0.name}: {0.scale:e}; systematics: {0.systematics!s}".format(self))
    @lazyload
    def tFile(self):
        from cppyy import gbl
        tf = gbl.TFile.Open(self.path)
        if not tf:
            logger.error("Could not open file {0}".format(self.path))
        return tf
    def getHist(self, plot, name=None, eras=None):
        """ Get the histogram for the combination of ``plot`` and this file/sample """
        hk = FileHist(hFile=self, plot=plot, name=name)
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
                lumi = config.luminosity[fCfg.era]
            elif isinstance(config.luminosity, numbers.Number):
                lumi = config.luminosity
            else:
                lumi = sum(lumi for era,lumi in iteritems(config.luminosity))
            mcScale = ( lumi*fCfg.cross_section*fCfg.branching_ratio / fCfg.generated_events )
            return mcScale*config.scale*fCfg.scale
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
    def getHist(self, plot, eras=None):
        """ Get the histogram for the combination of ``plot`` and this group of samples """
        return GroupHist(self, [ f.getHist(plot) for f in self.files if eras is None or f.cfg.era == eras or f.cfg.era in eras ])
    def __repr__(self):
        return "Group({0.name!r}, {0.files!r})".format(self)

class BaseHist(object):
    __slots__ = ("_obj", "_shape")
    def __init__(self):
        self._obj = None
        self._shape = None
    def nBins(self, axis):
        """ Number of (non-overflow) bins for an axis """
        return self.shape[axis]-2
    @property ## in fact this one can *always* be lazily loaded
    def obj(self):
        """ Default implementation: return cached value """
        return self._obj
    @property
    def shape(self):
        return self._shape
    @property
    def contents(self):
        """ Default implementation: view of the array in obj """
        return h1u.tarr_asnumpy(self.obj, shape=self.shape)
    @property
    def sumw2(self):
        """ Default implementation: view of the array in obj """
        if h1u.hasSumw2(self.obj):
            return h1u.tarr_asnumpy(self.obj.GetSumw2(), shape=self.shape)
        else:
            return self.contents
    def contributions(self):
        """ Default: just self """
        yield self
    def getCombinedSyst2(self, systematics): ## TODO move to BaseHist
        """ Calculate the combined systematic uncertainty on the sum """
        return getCombinedSyst2(list(self.contributions()), systematics)
    ## TODO access axes / binnings
    ## TODO getStyleOpt?

class MemHist(BaseHist):
    """ In-memory histogram, minimally compatible with :py:class:`~plotit.plotit.FileHist` """
    def __init__(self, obj):
        self._obj = obj
        self._shape = h1u.getShape(obj)

class FileHist(BaseHist):
    """
    Histogram from a file, or distribution for one sample.

    The actual object is only read into memory when first used.
    Transformations like scaling and rebinning are also applied then.
    In addition, references to the sample :py:class:`~plotit.plotit.File`
    and :py:class:`~plotit.config.Plot` are held.
    """
    __slots__ = ("name", "_tFile", "plot", "hFile", "systVars", "_syst2")
    def __init__(self, name=None, tFile=None, plot=None, hFile=None, systVars=None):
        """ Histogram key constructor. The object is read on first use, and cached.

        :param name:        name of the histogram inside the file (taken from ``plot`` if not specified)
        :param tFile:       ROOT file with histograms (taken from ``hFile`` if not specified)
        :param plot:        :py:class:`~plotit.config.Plot` configuration
        :param hFile:   :py:class:`plotit.plotit.File` instance corresponding to the sample
        """
        super(FileHist, self).__init__()
        self.name = name if name else plot.name
        self._tFile = tFile ## can be explicitly passed, or None (taken from hFile on first use then)
        self.plot = plot
        self.hFile = hFile
        self.systVars = systVars
        self._syst2 = None
    @property
    def tFile(self): ## only called if not constructed explicitly
        return self.hFile.tFile
    def __str__(self):
        return 'FileHist("{0}", "{1}")'.format(self.tFile.GetName(), self.name)
    def clone(self, name=None, tFile=None, plot=None, hFile=None, systVars=None):
        """ Modifying clone method. `systVars` is *not* included by default """
        return FileHist(name=(name if name is not None else self.name),
                        tFile=(tFile if tFile is not None else self.tFile),
                        plot=(plot if plot is not None else self.plot),
                        hFile=(hFile if hFile is not None else self.hFile),
                        systVars=systVars)
    @lazyload
    def obj(self):
        """ the underlying TH1 object """
        ## load the object from the file, and apply transformations as needed
        if ( not self.tFile ) or self.tFile.IsZombie() or ( not self.tFile.IsOpen() ):
            raise RuntimeError("File '{}'cannot be read".format(self.tFile))
        res = self.tFile.Get(self.name)
        if not res:
            raise KeyError("Could not retrieve key '{0}' from file {1}".format(self.name, (self.tFile.GetName() if self.tFile else repr(self.tFile))))
        ## scale/rebin/crop if needed
        scale = self.hFile.scale
        rebin = self.plot.rebin
        xOverflowRange = self.plot.x_axis_range
        if ( scale != 1. ) or ( rebin != 1 ) or ( xOverflowRange is not None ):
            res = h1u.cloneHist(res)
            if xOverflowRange is not None:
                res.GetXaxis().SetRangeUser(xOverflowRange[0], xOverflowRange[1])
                h1u.addOverflow(res, res.GetXaxis().GetFirst(), True )
                h1u.addOverflow(res, res.GetXaxis().GetLast() , False)
            if scale != 1.:
                if not h1u.hasSumw2(res):
                    res.Sumw2() ## NOTE should be automatic
                res.Scale(scale)
            if rebin != 1:
                res.Rebin(rebin)
            ## NOTE If scale/rebin are done in numpy (or later, when drawing), the copy of the histogram may be avoided
        self._shape = h1u.getShape(res) ## TODO take overflow into account ?
        return res
    @property
    def shape(self):
        self.obj ## load if needed
        return self._shape
    def getStyleOpt(self, name):
        return getattr(self.hFile.cfg, name)
    def __repr__(self):
        return "FileHist({0.name!r}, {0.hFile!r})".format(self)
    @lazyload
    def syst2(self):
        return self.getCombinedSyst2(self.systVars)

class SumHist(BaseHist):
    """
    Histogram that is the sum of other histograms (used for stack total, base of GroupHist)
    """
    __slots__ = ("entries", "_contents", "_sumw2", "_syst2")
    def __init__(self, entries=None):
        super(SumHist, self).__init__()
        self.entries = []
        self._contents = None
        self._sumw2 = None
        self._syst2 = None
        if entries:
            for entry in entries:
                self.add(entry, clearTotal=False)
    def add(self, entry, clearTotal=True):
        """ Add an entry to the sum (clearing the total, if already built) """
        ## TODO some kind of axis compatibility test (delayed, then, in contributions() or its users)
        self.entries.append(entry)
        if clearTotal:
            self.clear()
    def clear(self):
        if self._contents is not None:
            self._contents = None
        if self._sumw2 is not None:
            self._sumw2 = None
        if self._syst2 is not None:
            self._syst2 = None
        if self._obj is not None:
            self._obj = None
    @property
    def shape(self):
        if not self._shape: ## retrieve (and possibly load) if needed
            self._shape = self.entries[0].shape
        return self._shape
    @lazyload
    def obj(self):
        """ the underlying TH1 object """
        res = h1u.cloneHist(self.entries[0].obj)
        for entry in islice(self.entries, 1, None):
            res.Add(entry.obj)
        return res
    def contributions(self):
        for entry in self.entries:
            for contrib in entry.contributions():
                yield contrib
    @lazyload
    def contents(self):
        return sum(contrib.contents for contrib in self.contributions())
    @lazyload
    def sumw2(self):
        return sum(contrib.sumw2 for contrib in self.contributions())
    @lazyload
    def syst2(self):
        return self.getCombinedSyst2(set(chain.from_iterable(contrib.systVars for contrib in self.contributions())))

class GroupHist(SumHist):
    """
    Combined histogram for a group of samples (SumHist with a config)
    """
    __slots__ = ("group",)
    def __init__(self, group, entries):
        """ Constructor

        :param group: :py:class:`~plotit.plotit.Group` instance
        :param entries: a :py:lass:`~plotit.plotit.FileHist` for each sample in the group
        """
        super(GroupHist, self).__init__(entries)
        self.group = group
        ## TODO is self.plot needed? explicitly or as property
    def getStyleOpt(self, name):
        return getattr(self.group.cfg, name)

def getCombinedSyst2(contributions, systematics):
    """ Get the combined systematic uncertainty

    :param contributions: contributions (FileHist) to group over
    :param systematics:  systematic variations to consider (if None, all that are present are used for each histogram)
    """
    if not hasattr(contributions, "__iter__"):
        contributions = [ contributions ]
    shape = contributions[0].shape
    assert all(cb.shape == shape for cb in contributions)
    syst2 = np.zeros(shape)
    for syst in systematics:
        systInBins = np.zeros(shape)
        for contrib in contributions:
            svh = contrib.systVars.get(syst)
            if svh:
                systInBins += np.maximum(np.abs(svh.up-svh.nom), np.abs(svh.nom-svh.down))
        syst2 += systInBins**2
    return syst2

class Stack(SumHist):
    """
    Stack of distribution contributions from different samples.

    The entries are instances of either :py:class:`~plotit.plotit.FileHist` or
    :py:class:`~plotit.plotit.GroupHist`, for a single sample or a group of them,
    respectively.
    In addition to summing the histograms, helper methods to calculate the
    systematic uncertainty on the total, combined with the statistical uncertainty
    or not, are provided.
    """
    __slots__ = tuple()
    def __init__(self, entries=None):
        super(Stack, self).__init__(entries=entries)

    ## TODO absorbe in the draw backends, simple enough now
    def getSystematicHisto(self):
        """ construct a histogram of the stack total, with only systematic uncertainties """
        return h1u.h1With(self.obj, errors2=self.syst2)
    def getStatSystHisto(self):
        """ construct a histogram of the stack total, with statistical+systematic uncertainties """
        return h1u.h1With(self.obj, errors2=(self.sumw2 + self.syst2))
    def getRelSystematicHisto(self):
        """ construct a histogram of the relative systematic uncertainties for the stack total """
        ##relSyst2 = self.syst2 / h1u.tarr_asnumpy(self.total)**2
        return h1u.h1With(self.obj, values=np.ones(self.shape),
                    errors2=self.syst2/self.contents**2)

    ## TODO check if this still makes sense / is needed
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

def makeStackRatioPlots(plots, samples, systematics=None, config=None, outdir=".", backend="matplotlib", chunkSize=100, luminosity=0.):
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
                )) for plot in plots ]
    logger.debug("Drawing {0:d} plots, splitting in chunks of {1:d}".format(len(plots), chunkSize))
    ## load and draw, in chunks
    for i in range(0, len(stacks_per_plot), chunkSize):
        i_stacks_plots = stacks_per_plot[i:i+chunkSize]
        loadHistograms(chain.from_iterable(
            chain(dataStack.contributions(), mcStack.contributions(), sigHists)
            for plot, (dataStack, mcStack, sigHists) in i_stacks_plots))
        for plot, (dataStack, mcStack, sigHists) in i_stacks_plots:
            logger.debug("Drawing plot {0}".format(plot.name))
            drawStackRatioPlot(plot, mcStack, dataStack, outdir=outdir, config=config, luminosity=luminosity)
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
            if fl.cfg.group:
                try:
                    grp = next(g for g in groupConfigs if g.name == fl.cfg.group)
                    files_by_group[fl.cfg.group].append(fl)
                except StopIteration:
                    logger.warning("Group {0.cfg.group!r} of sample {0.name!r} not found, adding ungrouped".format(fl))
                    groups_and_samples.append(fl)
            else:
                groups_and_samples.append(fl)
    groups_and_samples += [ Group(gCfg.name, files_by_group[gCfg.name], gCfg)
            for gCfg in groupConfigs if gCfg.name in files_by_group ]
    return sorted(groups_and_samples, key=lambda f : f.cfg.order if f.cfg.order is not None else 0)

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

def resolveFiles(cFiles, config, systematics=None, histodir="."):
    """ Resolve paths, and construct :py:class:`plotit.plotit.File` objects (with TFile handles) from :py:class:`plotit.config.File` objects (pure configuration) """
    if systematics is None:
        systematics = []
    resolve = partial(getHistoPath, cfgRoot=config.root, baseDir=histodir)
    return [ File(fCfg.name, resolve(fCfg.name), fCfg, config=config, systematics=systematics) for fCfg in cFiles ]

def loadFromYAML(yamlFileName, histodir=".", eras=None):
    """
    Parse a plotIt YAML file

    :param yamlFileName: config file path
    :param histodir: base path for finding histograms (to be combined with ``'root'`` in configuration and the sample file names)
    :param eras: selected era, or list of selected eras (default: all that are present)

    :returns: tuple of configuration (``"configuration"`` block), list of samples (groups or ungrouped files), list of plots, list of systematic variations considered, and the legend configuration
    """
    from .config import parseWithIncludes
    yCfg = parseWithIncludes(yamlFileName)
    ## create config objects from YAML dictionary
    from .config import loadConfiguration, loadFiles, loadGroups, loadPlots, loadSystematics, loadLegend
    config = loadConfiguration(yCfg.get("configuration"))
    cFiles = loadFiles(yCfg.get("files"))
    cGroups = loadGroups(yCfg.get("groups"), files=cFiles)
    plots = loadPlots(yCfg.get("plots"), defaultStyle=config)
    systematics = loadSystematics(yCfg.get("systematics"), configuration=config)
    legend = loadLegend(yCfg.get("legend"))
    ## resolve, select, and sort files and groups into samples
    files = resolveFiles(cFiles, config, systematics=systematics, histodir=histodir)
    samples = samplesFromFilesAndGroups(files, cGroups, eras=(eras if eras is not None else config.eras))
    return config, samples, plots, systematics, legend

def plotItFromYAML(yamlFileName, histodir=".", outdir=".", eras=None, backend="matplotlib"):
    logger.info("Running like plotIt with config {0}, histodir={1}, outdir={1}".format(yamlFileName, histodir, outdir))
    config, samples, plots, systematics, legend = loadFromYAML(yamlFileName, histodir=histodir, eras=eras)
    makeStackRatioPlots(plots, samples, systematics=systematics, config=config, outdir=outdir, backend=backend, luminosity=config.getLumi(eras))

def makeBaseArgsParser(description=None):
    def optStrList(value):
        if value:
            return value.split(",")
    import argparse
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("yamlFile", help="plotIt configuration file (e.g. plots.yml)")
    parser.add_argument("--histodir", help="base path for finding histograms (to be combined with ``'root'`` in configuration and the sample file names; default: the directory that contains yamlFile)")
    parser.add_argument("--eras", type=optStrList, help="Era or (comma-separated) list of eras to consider")
    return parser

def inspectConfig():
    parser = makeBaseArgsParser(description="Load and interactively inspect a plotIt config")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    import os.path
    if args.histodir:
        histodir = args.histodir
    else:
        histodir = os.path.dirname(args.yamlFile)
    import logging
    logging.basicConfig(level=(logging.DEBUG if args.verbose else logging.INFO))
    config, samples, plots, systematics, legend = loadFromYAML(args.yamlFile, histodir=histodir, eras=args.eras)
    import IPython
    plots = { p.name: p for p in plots }
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
    plotItFromYAML(args.yamlFile, histodir=histodir, outdir=args.outdir, eras=args.eras, backend=args.backend)
