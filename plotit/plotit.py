from __future__ import absolute_import
"""
plotIt using matplotlib

Based on https://github.com/cp3-llbb/plotIt

WARNING: very much work-in-progress, many things are not implemented yet
"""
from future.utils import iteritems

from . import config
from . import histo_utils as h1u
from . import logger

class File(object):
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
    def getKey(self, plot, name=None):
        return HistoKey(histoFile=self, plot=plot, name=name)
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

def getFileOrder(hFile, groups=None):
    if hFile.order:
        return hFile.order
    elif groups and hFile.group in groups:
        return groups[hFile.group].order
    return 0

class MemHistoKey(object):
    """ mini-version for in-memory histograms """
    def __init__(self, obj):
        self.obj = obj
    def __getattr__(self, name):
        return getattr(self.obj, name)

class HistoKey(object):
    """
    TH1F wrapper to keep track of origin file, name and transformation

    Will lazily load (and cache) the object from the file,
    and apply scaling and rebinning as needed at that point.
    """
    __slots__ = ("_obj", "name", "tFile", "plot", "hFile")
    def __init__(self, name=None, tFile=None, plot=None, histoFile=None):
        """ Histogram key constructor. The object is read on first use, and cached.

        :param name:        name of the histogram inside the file (taken from ``plot`` if not specified)
        :param tFile:       ROOT file with histograms (taken from ``histoFile`` if not specified)
        :param plot:        :py:class:`plotit.config.Plot` configuration
        :param histoFile:   :py:class:`plotit.plotit.File` instance corresponding to the sample
        """
        self._obj = None
        self.name = name if name else plot.name
        self.tFile = tFile if tFile else histoFile._tf
        self.plot = plot
        self.hFile = histoFile
    def __str__(self):
        return 'HistoKey("{0}", "{1}")'.format(self.tFile.GetName(), self.name)
    def clone(self, name=None, tFile=None, plot=None, histoFile=None):
        """ Modifying clone method """
        return HistoKey(name=(name if name is not None else self.name),
                        tFile=(tFile if tfile is not None else self.tFile),
                        plot=(plot if plot is not None else self.plot),
                        histoFile=(histoFile if histoFile is not None else self.histoFile))
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
    def __getattr__(self, name):
        return getattr(self.obj, name)
    def getStyleOpt(self, name):
        return getattr(self.hFile.cfg, name)

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

    from .histstacksandratioplot import THistogramStack
    from .systematics import SystVarsForHist
    for pName, aPlot in iteritems(plots):
        obsStack = THistogramStack()
        expStack = THistogramStack()
        for f in files:
            hk = f.getKey(aPlot)
            if f.cfg.type == "data":
                obsStack.add(hk) ##, label=...
            elif f.cfg.type == "mc":
                expStack.add(hk, systVars=SystVarsForHist(hk, f.systematics)) ##, label=...

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
