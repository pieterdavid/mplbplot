from __future__ import absolute_import
"""
Classes related to loading configuration from YAML
"""
from . import logger
from itertools import chain
from future.utils import iteritems, itervalues
import numbers

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
    required_attributes = ("type",)
    optional_attributes = {
              "legend"          : ""
            , "legend-style"    : None
            , "legend-order"    : 0
            , "drawing-options" : None
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
        super(PlotStyle, self).__init__(**kwargs)
        if self.type:
            self.type = self.type.upper()

        if self.legend_style is None:
            if self.type == "MC":
                self.legend_style = "lf"
            elif self.type == "SIGNAL":
                self.legend_style = "l"
            elif self.type == "MC":
                self.legend_style = "pe"

        if self.drawing_options is None:
            if self.type in ("MC", "SIGNAL"):
                self.drawing_options = "hist"
            elif self.type == "DATA":
                self.drawing_options = "pe"
            else:
                self.drawing_options = ""

        black = PlotStyle.loadColor("#000000")
        if self.fill_color:
            self.fill_color = PlotStyle.loadColor(self.fill_color)
        elif self.type == "MC":
            self.fill_color = black
        if self.fill_type:
            pass
        elif self.type == "MC":
            self.fill_type = 1001
        elif self.type == "SIGNAL":
            self.fill_type = 0
        if self.line_width:
            pass
        elif self.type == "MC":
            self.line_width = 0
        else:
            self.line_width = 1
        if self.line_color:
            self.line_color = PlotStyle.loadColor(self.line_color)
        elif self.type != "MC":
            self.line_color = black
        if self.line_type is None and self.type == "SIGNAL":
            self.line_type = 2 ## TODO something matplotlib also understands
        if self.marker_color:
            self.marker_color = PlotStyle.loadColor(self.marker_color)
        elif self.type == "DATA":
            self.marker_color = black ## TODO look up
        if self.type == "DATA":
            if self.marker_size is None:
                self.marker_size = 1
            if self.marker_type is None:
                self.marker_type = 20

    @staticmethod
    def loadColor(color):
        if not ( color[0] == "#" and ( len(color) == 7 or len(color) == 9 ) ):
            raise ValueError("Color should be in the format '#RRGGBB' or '#RRGGBBAA' (got {!r})".format(color))
        r = int(color[1:3], base=16)/255.
        g = int(color[3:5], base=16)/255.
        b = int(color[5:7], base=16)/255.
        a = int(color[7:9], base=16)/255. if len(color) > 7 else 1.
        return (r,g,b,a)


class Group(PlotStyle):
    required_attributes = tuple(list(PlotStyle.required_attributes)+["name", "files"])
    optional_attributes = mergeDicts(PlotStyle.optional_attributes, {
              "order"            : None
            })
    def __init__(self, name, files, **kwargs):
        kwargs["name"] = name
        kwargs["files"] = files
        if files and ("type" not in kwargs):
            logger.debug("files: {0!r}".format(files))
            f0type = next(f for f in files).type
            if not all(f.type == f0type for f in files):
                logger.warning("Not all the files with group {0} have the same type: {1}".format(kwargs.get("name"), ", ".join("{0}: {1}".format(f.name, f.type) for f in files)))
            kwargs["type"] = f0type
        super(Group, self).__init__(**kwargs)

class File(PlotStyle):
    required_attributes = set(("type", "name"))
    optional_attributes = mergeDicts(PlotStyle.optional_attributes, {
              "pretty-name"      : None
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
        name = kwargs.get("name")
        super(File, self).__init__(**kwargs)
        self.type = self.type.upper()
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
            , "log-y-axis-range"          : None
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
            , "errors-type"               : "Poisson" ## TODO get from global ?
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

class Configuration(BaseYAMLObject):
    optional_attributes = {
              "width"                     : 800
            , "height"                    : 800
            , "margin-left"               : 0.17
            , "margin-right"              : 0.03
            , "margin-top"                : 0.05
            , "margin-bottom"             : 0.13
            #
            , "eras"                      : []
            , "luminosity"                : {}
            , "scale"                     : 1.
            , "no-lumi-rescaling"         : False
            , "luminosity-error"          : 0.
            #
            , "y-axis-format"             : "%1% / %2$.2f" ## TODO make this a python format
            , "ratio-y-axis-title"        : "Data / MC"
            , "ratio-style"               : "P0" ## TODO ???
            #
            , "error-fill-color"          : 42   ## TODO ???
            , "error-fill-style"          : 3154 ## TODO ???
            #
            , "fit-n-points"              : 1000
            , "fit-line-color"            : 46   ## TODO ???
            , "fit-line-width"            : 1    ## TODO ???
            , "fit-line-style"            : 1    ## TODO ???
            , "fit-error-fill-color"      : 42   ## TODO ???
            , "fit-error-fill-style"      : 1001 ## TODO ???
            , "ratio-fit-n-points"        : 1000
            , "ratio-fit-line-color"      : 46   ## TODO ???
            , "ratio-fit-line-width"      : 1    ## TODO ???
            , "ratio-fit-line-style"      : 1    ## TODO ???
            , "ratio-fit-error-fill-color": 42   ## TODO ???
            , "ratio-fit-error-fill-style": 1001 ## TODO ???
            # TODO line_style
            # , "labels" # TODO
            , "experiment"                : "CMS"
            , "extra-label"               : ""
            , "luminosity-label"          : ""
            , "root"                      : "."
            #
            , "transparent-background"    : False
            , "show-overflow"             : False ## TODO default for plot
            , "errors-type"               : "Poisson" ## TODO define types
            , "x-axis-label-size"         : 18
            , "y-axis-label-size"         : 18
            , "x-axis-top-ticks"          : True
            , "y-axis-right-ticks"        : True
            , "blinded-range-fill-color"  : 42   ## TODO ???
            , "blinded-range-fill-style"  : 1001 ## TODO ???
            }
    def __init__(self, **kwargs):
        super(Configuration, self).__init__(**kwargs)
    def getLumi(self, eras=None):
        if eras is None:
            if isinstance(self.luminosity, numbers.Number):
                return self.luminosity
            else:
                return sum(eraLumi for eraLumi in itervalues(self.luminosity))
        else:
            return sum(self.luminosity[era] for era in eras)

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

def parseWithIncludes(yamlPath):
    """ Parse a YAML file, with 'includes' relative to its path """
    cfg = _plotit_loadWrapper(yamlPath)
    basedir = os.path.dirname(yamlPath)
    _load_includes(cfg, basedir)
    return cfg

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

## Consistent set of helpers to load config objects from config dictionaries as found in the YAML

def loadPlots(plotsConfig=None, defaultStyle=None):
    """ Load a list of :py:class:`~plotit.config.Plot` instances from a config dictionary """
    if plotsConfig is None:
        return []
    plotDefaults = dict((attNm, getattr(defaultStyle, attnm)) for attNm,attDef in iteritems(PlotStyle.optional_attributes) if hasattr(defaultStyle, attNm) and getattr(defaultStyle, attNm) != attDef)
    return [ Plot(name=pName, **mergeDicts(plotDefaults, pConfig)) for pName, pConfig in iteritems(plotsConfig) ]

def loadSystematics(systConfigs=None, configuration=None):
    """ Load a list of :py:class:`~plotit.systematics.SystVar` instances from config entries"""
    if systConfigs is None:
        return []
    systs = [ parseSystematic(item) for item in systematics ]
    ## lumi systematic
    if configuration and configuration.luminosity_error != 0.:
        from .systematics import ConstantSystVar
        lumisyst = ConstantSystVar("lumi", 1.+configuration.luminosity_error, pretty_name="Luminosity")
        logger.debug("Adding luminosity systematic {0!r}".format(lumisyst))
        systs.append(lumisyst)
    return systs

def loadConfiguration(confConfig=None):
    """ Load a :py:class:`~plotit.config.Configuration` from a dict """
    if confConfig is None:
        confConfig = dict()
    return Configuration(**confConfig)

def loadFiles(fileConfigs=None):
    """ Load a list of :py:class:`~plotit.config.File` instances from a dictionary with settings """
    if fileConfigs is None:
        return []
    return [ File(name=name, **fileCfg) for name, fileCfg in iteritems(fileConfigs) ]

def loadGroups(groupConfigs=None, files=None, includeEmpty=False):
    if groupConfigs is None:
        return []
    if files is None:
        files = []
    groups = []
    for name, groupCfg in iteritems(groupConfigs):
        groupFiles = [ f for f in files if f.group ==name ]
        if includeEmpty or groupFiles:
            groups.append(Group(name, groupFiles, **groupCfg))
    return groups
