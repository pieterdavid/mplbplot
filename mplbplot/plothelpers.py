"""
Helper functions for making plots with matplotlib

Customization of matplotlib's default style
that cannot be done through matplotlibrc.

HandlerPolygonPathIfEmpty, fix_minus, ROOTScalarFormatter,
ROOTLogFormatter, and SymNormalize are slightly modified copies
of the corresponding classes included in matplotlib.
"""
__all__ = ( "histHandlerMap"
          , "ROOTScalarFormatter", "ROOTLogFormatter"
          , "SymNormalize"
          , "AxesWithPull"
          , "minorTicksOn", "labelsRight", "setMajorTickers", "rootMajorFormatter"
          , "formatAxes"
          )

import copy
import numpy as np

from itertools import ifilter, imap

import matplotlib.cbook
import matplotlib.colors
import matplotlib.lines
import matplotlib.legend
import matplotlib.legend_handler
import matplotlib.patches
import matplotlib.ticker

class HandlerPolygonAsPathIfEmpty(matplotlib.legend_handler.HandlerPatch):
    """
    Handler that adds a line if the patch is not filled (for step histograms)
    """
    def __init__(self, **kwargs):
        matplotlib.legend_handler.HandlerPatch.__init__(self, **kwargs)

    def create_artists(self, legend, orig_handle,
                       xdescent, ydescent, width, height, fontsize,
                       trans):
        if not orig_handle.fill: # using path instead
            xy = orig_handle.get_xy()
            origProps = orig_handle.properties()
            props = dict(imap( lambda (k,v) : (k,v) if not k.startswith("edge") else (k[4:], v),
                            ifilter( lambda (k,v) : k.startswith("line") or k.startswith("edge") or k in ("label",),
                                origProps.iteritems())))
            ln = matplotlib.lines.Line2D(xy[:,0], xy[:,1], marker=None, **props)
            handler = legend.get_legend_handler(legend.get_legend_handler_map(), ln)
            return handler.create_artists(legend, ln,
                                          xdescent, ydescent, width, height,
                                          fontsize,
                                          trans)
        else: # Fallback to actual patch
            return matplotlib.legend_handler.HandlerPatch.create_artists(self, legend, orig_handle,
                                               xdescent, ydescent, width, height,
                                               fontsize,
                                               trans)

## create a custom handler map
histHandlerMap = copy.deepcopy(matplotlib.legend.Legend.get_default_handler_map())
histHandlerMap[matplotlib.patches.Patch] = HandlerPolygonAsPathIfEmpty()

## from matplotlib.ticker.Formatter
def fix_minus(s):
    """ Replace hyphens with a unicode minus.  """
    from matplotlib import rcParams
    if rcParams['text.usetex'] or not rcParams['axes.unicode_minus']:
        return s
    else:
        return s.replace('-', '\u2212')

class ROOTScalarFormatter(matplotlib.ticker.ScalarFormatter):
    """
    Format values for linear axis (suppressing trailing zeros)

    derived from ScalarFormatter
    """
    def __call__(self, x, pos=None):
        """
        Return the format for tick value `x` at position `pos`.
        """
        if len(self.locs) == 0:
            return ''
        else:
            from matplotlib.ticker import is_close_to_int
            if abs(x) < 1e4 and is_close_to_int(x):
                return "%d" % int(np.round(x))
            else:
                s = self.pprint_val(x)
                return self.fix_minus(s)

class ROOTLogFormatter(matplotlib.ticker.LogFormatter):
    """
    Format values for log axis; using ``exponent = log_base(value)``

    derived from LogFormatterMathtext
    """

    def __call__(self, x, pos=None):
        'Return the format for tick val *x* at position *pos*'
        b = self._base
        import math
        from matplotlib.ticker import is_close_to_int, nearest_long

        # only label the decades
        if x == 0:
            return "$0$"

        fx = math.log(abs(x)) / math.log(b)
        is_decade = is_close_to_int(fx)

        sign_string = '-' if x < 0 else ''

        # use string formatting of the base if it is not an integer
        if b % 1 == 0.0:
            base = '%d' % b
        else:
            base = '%s' % b

        if not is_decade and self.labelOnlyBase:
            return ''
        elif not is_decade:
                return ('$%s%s^{%.2f}$') % \
                                            (sign_string, base, fx)
        else:
            if nearest_long(fx) == 0.:
                return ('$%s1$') % sign_string
            elif nearest_long(fx) == 1.:
                return ('$%s%s$') % (sign_string, base)
            else:
                return ('$%s%s^{%d}$') % (sign_string,
                                        base,
                                        nearest_long(fx))

class SymNormalize(matplotlib.colors.Normalize):
    """
    Normalize a given value to the 0-1 range, symmetrically around 0
    """
    def __init__(self, vmax=None, clip=False):
        """
        If *vmax* is not given, it is initialized from the maximum absolute
        value of the first input processed.  That is, *__call__(A)* calls
        *autoscale_None(A)*.
        If *clip* is *True* and the given value falls outside the range,
        the returned value will be 0 or 1, whichever is closer.

        Works with scalars or arrays, including masked arrays.  If
        *clip* is *True*, masked values are set to 1; otherwise they
        remain masked.  Clipping silently defeats the purpose of setting
        the over, under, and masked colors in the colormap, so it is
        likely to lead to surprises; therefore the default is
        *clip* = *False*.
        """
        self.vmax = vmax
        self.clip = clip
    @property
    def vmin(self):
        return -self.vmax
    @vmin.setter
    def vmin(self, val):
        self.vmax = abs(float(val))
    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        self.autoscale_None(result)
        vmax = abs(float(self.vmax))
        if vmax == 0.:
            result.fill(0)
        else:
            if clip:
                mask = np.ma.getmask(result)
                result = np.ma.array(np.clip(result.filled(vmax), -vmax, vmax), mask=mask)
            # ma division is very slow; we can take a shortcut
            resdat = result.data
            resdat += vmax
            resdat /= 2.*vmax
            result = np.ma.array(resdat, mask=result.mask, copy=False)
        if is_scalar:
            result = result[0]
        return result

    def inverse(self, value):
        if not self.scaled():
            raise ValueError("Not invertible until scaled")
        vmax = abs(float(self.vmax))

        if matplotlib.cbook.iterable(value):
            val = np.ma.asarray(value)
            return -vmax + val * 2.*vmax
        else:
            return -vmax + value * 2.*vmax

    def autoscale(self, A):
        """
        Set *vmax* to max absolute value of *A*.
        """
        self.vmax = np.ma.max(ma.abs(A))

    def autoscale_None(self, A):
        ' autoscale only None-valued vmax'
        if self.vmax is None and np.size(A) > 0:
            self.vmax = np.ma.max(np.ma.abs(A))

    def scaled(self):
        'return true if and vmax set'
        return (self.vmax is not None)



class AxesWithPull(object):
    """
    Resizes the given axes to fit a pull plot on top
    """
    def __init__(self, fig, dataAxes, vFracPull=0.15, vFracMargin=0.00, vFracTopMargin=0.00):
        self._fig = fig
        self.vFracPull = vFracPull
        self.vFracMargin = vFracMargin
        self.vFracTopMargin = vFracTopMargin
        self.dataAxes, self.pullAxes = self._adjustAxes(fig, dataAxes)
    def _adjustAxes(self, fig, dataAxes):
        origPos = dataAxes.get_position() ## Bbox
        x0, x1 = origPos.get_points()[0,0], origPos.get_points()[1,0]
        y0, y3 = origPos.get_points()[0,1], origPos.get_points()[1,1]
        y4 = y3 - (y3-y0)*self.vFracTopMargin
        y2 = y4 - (y3-y0)*self.vFracPull
        y1 = y2 - (y3-y0)*self.vFracMargin
        dataPos = mpl.transforms.Bbox(np.array([[ x0, y0 ],[ x1, y1 ]]))
        pullPos = mpl.transforms.Bbox(np.array([[ x0, y2 ],[ x1, y4 ]]))
        dataAxes.set_position(dataPos)
        if self.vFracPull > 0.:
            pullAxes = fig.add_axes(pullPos, sharex=dataAxes)
            return dataAxes, pullAxes
        else:
            return dataAxes, None

## Formatting helpers: axis labels and tickers

def _getAxisList(ax, axis="both"):
    axs = []
    if axis == "both" or axis == "x":
        axs.append(ax.xaxis)
    if axis == "both" or axis == "y":
        axs.append(ax.yaxis)
    return axs

def minorTicksOn(axis):
    """ Turn on minor ticks if needed """
    if axis.get_scale() == "linear":
        axis.set_minor_locator(matplotlib.ticker.AutoMinorLocator())

def labelsRight(axis):
    """ move the axis titles to the right or top """
    axis.label.set_ha("right")
    if axis.axis_name == "x":
        axis.label.set_x(1.)
    elif axis.axis_name == "y":
        axis.label.set_y(1.)

def setMajorTickers(axis, nTicks=6):
    """ Reduce the number of ticks by about a factor two
    
    (6 major ticks) """
    majLoc = axis.get_major_locator()
    if isinstance(majLoc, matplotlib.ticker.MaxNLocator): # lin
        majLoc.set_params(nbins=nTicks)
    elif isinstance(majLoc, matplotlib.ticker.LogLocator): # log
        majLoc.numticks = nTicks

def rootMajorFormatter(axis):
    """ """
    if axis.get_scale() == "linear":
        axis.set_major_formatter(ROOTScalarFormatter())
    elif axis.get_scale() == "log":
        axis.set_major_formatter(ROOTLogFormatter(base=axis._scale.base))

def formatAxes(ax, axis="both"):
    """ Change default matplotlib axes formatting to ROOT-like

    - axis titles righ-aligned
    - minor ticks always on
    - fewer major ticks
    
    The optional `axis` argument ("both" by default) can be used
    to apply this only to one of the axes.
    """
    for iax in _getAxisList(ax, axis=axis):
        ## labels
        labelsRight(iax)
        ## ticks
        minorTicksOn(iax)
        setMajorTickers(iax, nTicks=11)
        ## formatters
        rootMajorFormatter(iax)
