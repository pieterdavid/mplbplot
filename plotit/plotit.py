from __future__ import absolute_import
"""
plotIt using matplotlib

Based on https://github.com/cp3-llbb/plotIt

WARNING: very much work-in-progress, many things are not implemented yet
"""
from . import logger
from future.utils import iteritems, itervalues

from collections import OrderedDict as odict

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

    scaleAndSystematicsPerFile = odict((f,
        (getScaleForFile(f, config), dict((syst.name, syst) for syst in systematics if f.type != "data" and syst.on(fN, f)))
        ) for fN,f in sorted(iteritems(files), key=lambda itm : getOrder(itm[1], groups=groups), reverse=True))

    from .histstacksandratioplot import THistogramStack
    from .systematics import SystVarsForHist
    for pName, aPlot in iteritems(plots):
        obsStack = THistogramStack()
        expStack = THistogramStack()
        for f, (fScale, fSysts) in iteritems(scaleAndSystematicsPerFile):
            logger.debug("Scale and systematics for file {0}: {1:f} {2!s}".format(f.pretty_name, fScale, fSysts))
            hk = f.getKey(pName, scale=fScale, rebin=aPlot.rebin, xOverflowRange=(aPlot.x_axis_range if aPlot.show_overflow else None))
            if f.type == "data":
                obsStack.add(hk) ##, label=..., drawOpts=...
            elif f.type == "mc":
                expStack.add(hk, systVars=SystVarsForHist(hk, fSysts), drawOpts={"fill_color":f.fill_color}) ##, label=..., drawOpts=...

        drawPlot(aPlot, expStack, obsStack, outdir=outdir)


def plotItFromYAML(yamlFileName, histodir=".", outdir="."):
    from .config import load as load_plotIt_YAML
    logger.info("Running like plotIt with config {0}, histodir={1}, outdir={1}".format(yamlFileName, histodir, outdir))
    config, files, groups, plots, systematics = load_plotIt_YAML(yamlFileName, histodir=histodir)
    ### get list of files, get list of systs, dict of systs per file; then list of plots: for each plot build the stacks and draw
    ## TODO cfg -> config
    plotIt(plots, files, groups=groups, systematics=systematics, config=config, outdir=outdir)

if __name__ == "__main__": ## quick test of basic functionality
    import ROOT
    ROOT.PyConfig.IgnoreCommandLineOptions = True
    import os.path
    my_plotit_dir = "" ## FIXME
    plotItFromYAML(os.path.join(my_plotit_dir, "examples/example.yml"))
    from matplotlib import pyplot as plt
    plt.show()
