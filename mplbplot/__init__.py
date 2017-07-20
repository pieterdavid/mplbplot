"""
mplbplot

Simple and customizable plotting of ROOT objects (TH1, TH2, TGraph...) with matplotlib

See https://github.com/pieterdavid/mplbplot for more information
"""
__version__ = "0.1.0"

## workaround for a problem with loading of graphics libraries
## make sure we don't import matplotlib before ROOT
import ROOT
ROOT.kTRUE
