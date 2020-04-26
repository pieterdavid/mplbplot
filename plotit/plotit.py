from __future__ import absolute_import
"""
plotIt using matplotlib

Based on https://github.com/cp3-llbb/plotIt

WARNING: very much work-in-progress, many things are not implemented yet
"""
from . import logger
from future.utils import iteritems

from collections import OrderedDict as odict

from . import config

from .systematics import HistoKey

class File(object):
    __slots__ = ("name", "path", "cfg", "_tf")
    def __init__(self, name, path, cfg):
        self.name = name
        self.path = path
        self.cfg = cfg
        from cppyy import gbl
        self._tf = gbl.TFile.Open(self.path)
    def getKey(self, name, **kwargs):
        return HistoKey(self._tf, name, **kwargs)

def getScaleForFile(f, config):
    """ Infer the scale factor for histograms from the file dict and the overall config """
    if f.type == "data":
        return 1.
    else:
        if f.era:
            lumi = config["eras"][f.era]["luminosity"]
        else:
            lumi = config["luminosity"]
        mcScale = ( lumi*f.cross_section*f.branching_ratio / f.generated_events )
        if config.get("ignore-scales", False):
            return mcScale
        else:
            return mcScale*config.get("scale", 1.)*f.scale

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

    def getOrder(hFile, groups=None):
        if hFile.order:
            return hFile.order
        elif groups and hFile.group in groups:
            return groups[hFile.group].order
        return 0

    scaleAndSystematicsPerFile = list((f, getScaleForFile(f.cfg, config),
        dict((syst.name, syst) for syst in systematics if f.cfg.type != "data" and syst.on(f.name, f.cfg)))
        for f in sorted(files, key=lambda itm : getOrder(itm.cfg, groups=groups), reverse=True))

    from .histstacksandratioplot import THistogramStack
    from .systematics import SystVarsForHist
    for pName, aPlot in iteritems(plots):
        obsStack = THistogramStack()
        expStack = THistogramStack()
        for f, fScale, fSysts in scaleAndSystematicsPerFile:
            logger.debug("Scale and systematics for file {0}: {1:f} {2!s}".format(f.cfg.pretty_name, fScale, fSysts))
            hk = f.getKey(pName, scale=fScale, rebin=aPlot.rebin, xOverflowRange=(aPlot.x_axis_range if aPlot.show_overflow else None))
            if f.cfg.type == "data":
                obsStack.add(hk) ##, label=..., drawOpts=...
            elif f.cfg.type == "mc":
                expStack.add(hk, systVars=SystVarsForHist(hk, fSysts), drawOpts={"fill_color":f.cfg.fill_color}) ##, label=..., drawOpts=...

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
    files = [ File(fNm, _plotIt_histoPath(fNm, config["root"], histodir), fCfg) for fNm, fCfg in fileCfgs.items() ]
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
