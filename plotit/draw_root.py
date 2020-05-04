from __future__ import absolute_import
"""
python version of plotIt/TH1Plotter
"""
import os.path
from . import logger
from . import histo_utils as h1u
from cppyy import gbl
from itertools import product

_color_index = 5000
color_cache = {}
def loadColor(color):
    global _color_index
    if color not in color_cache:
        r,g,b,a = color
        color_cache[color] = (_color_index, gbl.TColor(_color_index, r, g, b, str(color), a))
        _color_index += 1
    return color_cache[color][0]

_style = None
def loadStyle(config):
    global _style
    TITLE_FONTSIZE = 26
    LABEL_FONTSIZE = 18

    style = gbl.TStyle("style", "style")
    # For the canvas:
    style.SetCanvasBorderMode(0)
    style.SetCanvasColor(gbl.kWhite)
    style.SetCanvasDefH(800) #Height of canvas
    style.SetCanvasDefW(800) #Width of canvas
    style.SetCanvasDefX(0)   #POsition on screen
    style.SetCanvasDefY(0)
    # For the Pad:
    style.SetPadBorderMode(0)
    style.SetPadColor(gbl.kWhite)
    style.SetPadGridX(False)
    style.SetPadGridY(False)
    style.SetGridColor(0)
    style.SetGridStyle(3)
    style.SetGridWidth(1)
    # For the frame:
    style.SetFrameBorderMode(0)
    style.SetFrameBorderSize(1)
    style.SetFrameFillColor(0)
    style.SetFrameLineColor(1)
    style.SetFrameLineStyle(1)
    style.SetFrameLineWidth(1)
    # For the histo:
    style.SetHistLineColor(1)
    style.SetHistLineStyle(0)
    style.SetHistLineWidth(1)

    style.SetEndErrorSize(2)
    #  style.SetErrorMarker(20)
    #style.SetErrorX(0)

    style.SetMarkerStyle(20)

    # For the fit/function:
    style.SetOptFit(1)
    style.SetFitFormat("5.4g")
    style.SetFuncColor(2)
    style.SetFuncStyle(1)
    style.SetFuncWidth(1)

    # For the date:
    style.SetOptDate(0)

    # For the statistics box:
    style.SetOptFile(0)
    style.SetOptStat(0); # To display the mean and RMS:   SetOptStat("mr")
    style.SetStatColor(gbl.kWhite)
    style.SetStatFont(43)
    style.SetStatFontSize(0.025)
    style.SetStatTextColor(1)
    style.SetStatFormat("6.4g")
    style.SetStatBorderSize(1)
    style.SetStatH(0.1)
    style.SetStatW(0.15)

    # Margins:
    style.SetPadTopMargin(config.margin_top)
    style.SetPadBottomMargin(config.margin_bottom)
    style.SetPadLeftMargin(config.margin_left)
    style.SetPadRightMargin(config.margin_right)

    # For the Global title:
    style.SetOptTitle(0)
    style.SetTitleFont(63)
    style.SetTitleColor(1)
    style.SetTitleTextColor(1)
    style.SetTitleFillColor(10)
    style.SetTitleFontSize(TITLE_FONTSIZE)

    # For the axis titles:

    style.SetTitleColor(1, "XYZ")
    style.SetTitleFont(43, "XYZ")
    style.SetTitleSize(TITLE_FONTSIZE, "XYZ")
    style.SetTitleXOffset(3.5)
    style.SetTitleYOffset(2.5)

    style.SetLabelColor(1, "XYZ")
    style.SetLabelFont(43, "XYZ")
    style.SetLabelOffset(0.01, "YZ")
    style.SetLabelOffset(0.015, "X")
    style.SetLabelSize(LABEL_FONTSIZE, "XYZ")

    style.SetAxisColor(1, "XYZ")
    style.SetStripDecimals(True)
    style.SetTickLength(0.02, "XYZ")
    style.SetNdivisions(510, "XYZ")

    style.SetPadTickX(1 if config.x_axis_top_ticks else 0)  # To get tick marks on the opposite side of the frame
    style.SetPadTickY(1 if config.y_axis_right_ticks else 0)

    style.SetOptLogx(0)
    style.SetOptLogy(0)
    style.SetOptLogz(0)

    style.SetHatchesSpacing(1.3)
    style.SetHatchesLineWidth(1)

    style.cd()
    _style = (style, config)

    return style

def setHistogramStyle(hk, h=None):
    if not h:
        h = hk.obj
    if hk.getStyleOpt("fill_color"):
        h.SetFillColor(loadColor(hk.getStyleOpt("fill_color")))
    if hk.getStyleOpt("fill_type"):
        h.SetFillStyle(hk.getStyleOpt("fill_type"))
    if hk.getStyleOpt("line_color"):
        h.SetLineColor(loadColor(hk.getStyleOpt("line_color")))
    if hk.getStyleOpt("line_width"):
        h.SetLineWidth(hk.getStyleOpt("line_width"))
    if hk.getStyleOpt("line_type"):
        h.SetLineStyle(hk.getStyleOpt("line_type"))
    if hk.getStyleOpt("marker_size"):
        h.SetMarkerSize(hk.getStyleOpt("marker_size"))
    if hk.getStyleOpt("marker_color"):
        h.SetMarkerColor(loadColor(hk.getStyleOpt("marker_color")))
    if hk.getStyleOpt("marker_type"):
        h.SetMarkerStyle(hk.getStyleOpt("marker_type"))
    if hk.getStyleOpt("type") == "MC" and hk.getStyleOpt("line_color") is None and hk.getStyleOpt("fill_color") is not None:
        h.SetLineColor(loadColor(hk.getStyleOpt("fill_color")))

def drawStackRatioPlot(plot, expStack, obsStack, sigStacks=None, config=None, outdir=".", luminosity=0.):
    if sigStacks is None:
        sigStacks = []
    if config is None:
        raise ValueError("Need a basic plotIt global config")

    global _style
    if _style is None or _style[1] != config:
        loadStyle(config)

    output_suffix = ""
    
    cv = gbl.TCanvas(plot.name, plot.name, config.width, config.height)
    if config.transparent_background:
        cv.SetFillStyle(4000)
        cv.SetFrameFillStyle(4000)

    toDraw = []
    if expStack.entries:
        h_mc = gbl.THStack("mc_{0}".format(plot.name), "mc_{0}".format(plot.name))
        for entry in (sorted(expStack.entries, key=lambda en : en.Integral())
                        if plot.sort_by_yields else expStack.entries):
            setHistogramStyle(entry)
            h_mc.Add(entry.obj, entry.getStyleOpt("drawing_options"))

        toDraw.append((h_mc, ""))
    if not plot.no_data:
        h_data = obsStack.total
        setHistogramStyle(obsStack.entries[0], h_data)
        h_data.Sumw2(False) ## disable Sumw2
        h_data.SetBinErrorOption(getattr(gbl.TH1, "k{0}".format(plot.errors_type)))
        ## TODO support for blinding (if requested)
        toDraw.append((h_data, obsStack.entries[0].getStyleOpt("drawing_options"))) ## TODO default from file, as for others in PlotStyle

    ## TODO add signals

    minimum = min((min(stE.GetMinimum() for stE in obj.GetStack()) if isinstance(obj, gbl.THStack) else obj.GetMinimum()) for obj,drwOpt in toDraw)
    minimum_pos = min((min(stE.GetMinimum(0) for stE in obj.GetStack()) if isinstance(obj, gbl.THStack) else obj.GetMinimum(0)) for obj,drwOpt in toDraw)

    showRatio = plot.show_ratio and expStack.entries and ( ( not plot.no_data ) and obsStack.entries )

    if showRatio:
        hi_pad = gbl.TPad("pad_hi", "", 0., 0.33333, 1., 1.)
        hi_pad.Draw()
        hi_pad.SetTopMargin(config.margin_top/.6666)
        hi_pad.SetLeftMargin(config.margin_left)
        hi_pad.SetBottomMargin(0.15)
        hi_pad.SetRightMargin(config.margin_right)


        low_pad = gbl.TPad("pad_lo", "", 0., 0., 1., 0.33333)
        low_pad.Draw()
        low_pad.SetTopMargin(1.)
        low_pad.SetLeftMargin(config.margin_left)
        low_pad.SetBottomMargin(config.margin_bottom/.3333)
        low_pad.SetRightMargin(config.margin_right)
        low_pad.SetTickx(1)

        hi_pad.cd()

    toDraw_s = sorted(toDraw, key=lambda itm : itm[0].GetMaximum(), reverse=True)
    maximum = toDraw_s[0][0].GetMaximum() ## TODO update with systematics from MC stack(s), if necessary
    toDraw_s[0][0].Draw(toDraw_s[0][1])
    for itm in toDraw_s:
        obj, opt = itm
        obj.Draw("{0} SAME".format(opt))

    ## TODO lines

    axHist = toDraw_s[0][0]
    axHist.Draw("AXIS SAME")

    ## then plot the ratio

    ## TODO create legend (skipping for now)

    topMargin = config.margin_top / ( .6666 if showRatio else 1. )

    gbl.TGaxis.SetExponentOffset(-0.06, 0, "y")

    if config.luminosity_label:
        ptlum = gbl.TPaveText(config.margin_left, 1-.5*topMargin, 1-config.margin_right, 1, "brNDC")
        ptlum.SetFillStyle(0)
        ptlum.SetFillStyle(0)
        ptlum.SetBorderSize(0)
        ptlum.SetMargin(0)
        ptlum.SetTextFont(42)
        ptlum.SetTextSize(0.6*topMargin)
        ptlum.SetTextAlign(33)
        try:
            lbl = config.luminosity_label.format(luminosity/1000.)
        except KeyError as ex:
            lbl = config.luminosity_label.replace("1$", "") % (luminosity/1000.)
        ptlum.AddText(lbl)
        ptlum.Draw()
    if config.experiment:
        ptexp = gbl.TPaveText(config.margin_left, 1-.5*topMargin, 1-config.margin_right, 1, "brNDC")
        ptexp.SetFillStyle(0);
        ptexp.SetBorderSize(0);
        ptexp.SetMargin(0);
        ptexp.SetTextFont(62);
        ptexp.SetTextSize(0.75*topMargin);
        ptexp.SetTextAlign(13);
        text = config.experiment
        if config.extra_label or plot.extra_label:
            text = "{0} #font[52]{{#scale[0.76]{{{1}}}}}".format(config.experiment,
                    (plot.extra_label if plot.extra_label else config.extra_label))
        ptexp.AddText(text)
        ptexp.Draw()

    ## TODO labels

    for logx, logy in product(
            ([False, True] if isinstance(plot.log_x, str) and plot.log_x.upper() == "BOTH" else [plot.log_x]),
            ([False, True] if isinstance(plot.log_y, str) and plot.log_y.upper() == "BOTH" else [plot.log_y])):

        xRange = plot.x_axis_range
        yRange = plot.log_y_axis_range if logy and plot.log_y_axis_range else plot.y_axis_range
        if xRange:
            axHist.GetXaxis().SetRangeUser(*xRange)
            if showRatio:
                pass
        if yRange:
            axHist.SetMinimum(yRange[0])
            axHist.SetMaximum(yRange[1])
        else:
            axHist.SetMaximum(maximum*(9. if logy else 1.2))
            if logy:
                if minimum <= 0.:
                    logger.warning("Detected minimum is negative {0:f} but log scale is on. Setting minimum to 0.1".format(minimum))
                    axHist.SetMinimum(.1)
                else:
                    axHist.SetMinimum(minimum)
            else:
                if plot.y_axis_show_zero:
                    axHist.SetMinimum(0)
                else:
                    axHist.SetMinimum(minimum*(1.2 if minimum < 0. else .8))

        if showRatio:
            if logx:
                hi_pad.SetLogx()
            if logy:
                hi_pad.SetLogy()
                low_pad.SetLogy()
        else:
            if logx:
                cv.SetLogx()
            if logy:
                cv.SetLogy()

        gbl.gPad.Modified()
        gbl.gPad.Update()

        output_suffix = "{0}{1}".format(("_logy" if logy else ""), ("_logx" if logx else ""))
        for ext in plot.save_extensions:
            outName = os.path.join(outdir, "{0}{1}.{2}".format(plot.name, output_suffix, ext))
            logger.debug("Saving as {0}".format(outName))
            cv.SaveAs(outName)
