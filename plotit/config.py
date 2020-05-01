from __future__ import absolute_import
"""
Classes related to loading configuration from YAML
"""
from . import logger
from itertools import chain
from future.utils import iteritems, itervalues

def mergeDicts(first, second):
    """ trivial helper: copy first, update with second and return """
    md = dict(first)
    md.update(second)
    return md

class BaseYAMLObject(object):
    """ Base class for objects constructed from YAML """
    required_attributes = set()
    optional_attributes = dict()
    @staticmethod
    def _normalizeAttr(att):
        return att.replace("-", "_")
    @staticmethod
    def _normalizeKeys(aDict):
        return dict((BaseYAMLObject._normalizeAttr(k), v) for k, v in iteritems(aDict))
    def __init__(self, **kwargs):
        if not all( nm in kwargs for nm in self.__class__.required_attributes ):
            raise KeyError("Attribute(s) {1} required for class {0} but not found (full dictionary: {2})".format(self.__class__.__name__, ", ".join("'{}'".format(k) for k in self.__class__.required_attributes if k not in kwargs), str(kwargs)))
        if not all( k in self.__class__.required_attributes or k in self.__class__.optional_attributes for k in kwargs ):
            raise KeyError("Unknown attribute(s) for class {0}: {1} (all attributes: {2})".format(self.__class__.__name__, ", ".join("'{}'".format(k) for k in kwargs if k not in self.__class__.required_attributes and k not in self.__class__.optional_attributes), str(kwargs)))
        self.__dict__.update(BaseYAMLObject._normalizeKeys(self.__class__.optional_attributes))
        self.__dict__.update(BaseYAMLObject._normalizeKeys(kwargs))
    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, ", ".join("{0}={1!r}".format(k,getattr(self, BaseYAMLObject._normalizeAttr(k))) for k in chain(self.__class__.required_attributes, (dk for dk,dv in iteritems(self.__class__.optional_attributes) if dv is not getattr(self, BaseYAMLObject._normalizeAttr(dk))))))

class PlotStyle(BaseYAMLObject):
    optional_attributes = {
              "legend"          : ""
            , "legend-style"    : None
            , "legend-order"    : 0
            , "drawing-options" : ""
            , "marker-size"     : None
            , "marker-color"    : None
            , "marker-type"     : None
            , "fill-color"      : None
            , "fill-type"       : None
            , "line-width"      : None
            , "line-color"      : None
            , "line-type"       : None
            }
    def __init__(self, **kwargs):
        typ = kwargs.get("type", "MC").upper()
        super(PlotStyle, self).__init__(**kwargs)

        if typ == "MC":
            self.legend_style = "lf"
        elif typ == "SIGNAL":
            self.legend_style = "l"
        elif typ == "MC":
            self.legend_style = "pe"

        if not self.drawing_options:
            if typ in ("MC", "SIGNAL"):
                self.drawing_options = "hist"
            elif typ == "DATA":
                self.drawing_options = "pe"

        if self.fill_color:
            self.fill_color = PlotStyle.loadColor(self.fill_color)
        if self.line_color:
            self.line_color = PlotStyle.loadColor(self.line_color)
        if self.marker_color:
            self.marker_color = PlotStyle.loadColor(self.marker_color)

    @staticmethod
    def loadColor(color):
        if not ( color[0] == "#" and ( len(color) == 7 or len(color) == 9 ) ):
            raise ValueError("Color should be in the format '#RRGGBB' or '#RRGGBBAA' (got {!r})".format(color))
        r = int(color[1:3], base=16)/255.
        g = int(color[3:5], base=16)/255.
        b = int(color[5:7], base=16)/255.
        a = int(color[7:9], base=16)/255. if len(color) > 7 else 1.
        return (r,g,b,a)


class Group(BaseYAMLObject):
    optional_attributes = mergeDicts(PlotStyle.optional_attributes, {
              "order"            : None
            })
    def __init__(self, files, **kwargs):
        self.files = files
        self.type = None
        super(Group, self).__init__(**kwargs)

class File(PlotStyle):
    required_attributes = set(("type",))
    optional_attributes = mergeDicts(PlotStyle.optional_attributes, {
              "pretty-name"      : None
            , "type"             : "MC"
            ##
            , "scale"            : 1.
            , "cross-section"    : None
            , "branching-ratio"  : 1.
            , "generated-events" : None
            ##
            , "group"            : None ## ??
            , "yields-title"     : None ## ??
            , "yields-group"     : None
            , "legend-group"     : None
            ##
            , "order"            : None
            , "era"              : None
            })
    def __init__(self, **kwargs):
        name = kwargs.pop("name")
        super(File, self).__init__(**kwargs)
        if self.pretty_name is None:
            self.pretty_name = name
        if self.yields_group is None:
            if self.group is not None:
                self.yields_group = self.group
            elif self.legend is not None:
                self.yields_group = self.legend
            else:
                self.yields_group = name

class Point(BaseYAMLObject):
    required_attributes = set(("x", "y"))
    def __init__(self, **kwargs):
        super(Point, self).__init__(**kwargs)

class Label(BaseYAMLObject):
    required_attributes = set(("text", "position"))
    optional_attributes = { "size" : 18 }
    def __init__(self, **kwargs):
        super(Label, self).__init__(**kwargs)
        self.position = Point(self.position)

class Plot(BaseYAMLObject):
    required_attributes = set(("name",))
    optional_attributes = {
              "exclude"                   : ""
            , "x-axis"                    : ""
            , "x-axis-format"             : ""
            , "y-axis"                    : ""
            , "y-axis-format"             : None
            , "normalized"                : False
            , "no-data"                   : False
            , "override"                  : False
            , "log-y"                     : False
            , "log-x"                     : False
            , "save-extensions"           : tuple()
            , "book-keeping-folder"       : ""
            , "show-ratio"                : False
            , "fit"                       : False
            , "fit-ratio"                 : False
            #
            , "fit-function"              : ""
            , "fit-legend"                : ""
            , "fit-legend-position"       : None
            , "fit-range"                 : None
            #
            , "ratio-fit-function"        : ""
            , "ratio-fit-legend"          : ""
            , "ratio-fit-legend-position" : None
            , "ratio-fit-range"           : None
            #
            , "show-errors"               : True
            , "x-axis-range"              : None
            , "y-axis-range"              : None
            , "ratio-y-axis-range"        : None
            , "blinded-range"             : None
            , "y-axis-show-zero"          : None
            , "inherits-from"             : None
            , "rebin"                     : 1
            , "labels"                    : []
            , "extra-label"               : None
            , "legend-position"           : None
            , "legend-columns"            : None
            , "show-overflow"             : None
            , "errors-type"               : None
            #
            , "binning-x"                 : None
            , "binning-y"                 : None
            , "draw-string"               : None
            , "selection-string"          : None
            #
            , "for-yields"                : True
            , "yields-title"              : True
            , "yields-table-order"        : True
            , "sort-by-yields"            : False
            #
            , "vertical-lines"            : []
            , "horizontal-lines"          : []
            , "lines"                     : []
            }
    def __init__(self, **kwargs):
        super(Plot, self).__init__(**kwargs)
        #if self.x_axis_range is not None:
        #    try:
        #        lims = tuple(float(tok.strip()) for tok in self.x_axis_range.strip("[]").split(","))
        #        if len(lims) != 2:
        #            raise ValueError("")
        #    except Exception, e:
        #        raise ValueError("Could not parse x-axis-range {0}: {1}".format(self.x_axis_range, e))
        #    self.x_axis_range = lims
        self.labels = [ Label(lblNd) for lblNd in self.labels ]

def _plotit_loadWrapper(fpath):
    """ yaml.safe_load from path """
    import yaml
    with open(fpath) as f:
        res = yaml.safe_load(f)
    return res

import os.path

def _load_includes(cfgDict, basePath):
    updDict = dict()
    for k,v in iteritems(cfgDict):
        if isinstance(v, dict):
            if len(v) == 1 and next(k for k in v) == "include":
                vals = v[next(k for k in v)]
                newDict = dict()
                for iPath in vals:
                    if not os.path.isabs(iPath):
                        iPath = os.path.join(basePath, iPath)
                    if not os.path.exists(iPath):
                        raise IOError("Included path '{}' does not exist".format(iPath))
                    newDict.update(_plotit_loadWrapper(iPath))
                updDict[k] = newDict
                _load_includes(newDict, basePath)
            else:
                _load_includes(v, basePath)
    cfgDict.update(updDict)

def parseSystematic(item):
    from .systematics import ShapeSystVar, ConstantSystVar, LogNormalSystVar
    if isinstance(item, str):
        return ShapeSystVar(item)
    elif isinstance(item, dict):
        if len(item) == 1:
            name, val = next(iteritems(item))
            if isinstance(val, float):
                return ConstantSystVar(name, val)
            elif isinstance(val, dict):
                if val["type"] == "shape":
                    syst = ShapeSystVar(name)
                elif val["type"] == "const":
                    syst = ConstantSystVar(name, val["value"])
                elif val["type"] in ("lognormal", "ln"):
                    cfg = dict((k.replace("-", "_"), v) for k, v in iteritems(val))
                    cfg.pop("type")
                    prior = cfg.pop("prior")
                    syst = LogNormalSystVar(name, prior, **cfg)
                if "pretty-name" in val:
                    syst.pretty_name = val["pretty-name"]
                if True in val:
                    import re
                    pat = re.compile(val[True])
                    syst.on = ( lambda aPat : ( lambda fName,fObj : bool(aPat.match(fName)) ) )(pat) ## FIXME on is automatically parsed to True, isMC and ...
                return syst
    else:
        raise ValueError("Invalid systematics node, must be either a string or a map")

def load(mainPath, vetoFileAttributes=None):
    if vetoFileAttributes is None:
        vetoFileAttributes = tuple()
    ## load config, with includes
    cfg = _plotit_loadWrapper(mainPath)
    basedir = os.path.dirname(mainPath)
    _load_includes(cfg, basedir)
    configuration = cfg["configuration"]
    plotDefaults = dict((k,v) for k,v in iteritems(configuration) if k in ("y-axis-format", "show-overflow", "errors-type"))
    ## files and groups
    files = dict((name, File(name=name, **dict((ak,av) for ak,av in iteritems(fileCfg) if ak not in vetoFileAttributes)))
            for name, fileCfg in iteritems(cfg["files"]))
    groups = dict()
    for name, groupCfg in iteritems(cfg.get("groups", dict())):
        groupFiles = dict((fName, f) for fName, f in iteritems(files) if f.group == name)
        if groupFiles:
            group = Group(groupFiles, **groupCfg)
            group.type = next(v for v in itervalues(groupFiles)).type
            groups[name] = group
    plots = dict((k, Plot(name=k, **mergeDicts(plotDefaults, v))) for k, v in iteritems(cfg.get("plots", {})))
    systematics = [ parseSystematic(item) for item in cfg.get("systematics", []) ]
    ## lumi systematic
    lumi_err = configuration.get("luminosity-error", 0.)
    if lumi_err != 0.:
        from .systematics import ConstantSystVar
        lumisyst = ConstantSystVar("lumi", 1.+lumi_err, pretty_name="Luminosity")
        logger.debug("Adding luminosity systematic {0!r}".format(lumisyst))
        systematics.append(lumisyst)

    return configuration, files, groups, plots, systematics
