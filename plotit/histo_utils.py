"""
Utility functions to manipulate ROOT histograms (for overflow display and systematics)
"""
__all__ = ("cloneHist", "addOverflow",
           "histoWithErrors", "histoWithErrorsQuadAdded", "histoDivByValues",
           "divide")

from builtins import zip, range
from itertools import count, chain
import numpy as np

from cppyy import gbl
gbl.TH1.AddDirectory(False)

def cloneHist(hist, newName=None):
    if gbl.TH1.AddDirectoryStatus():
        raise AssertionError("Cannot clone histograms as free objects when TH1::AddDirectoryStatus is True")
    return ( hist.Clone(newName) if newName else hist.Clone() )

def sumBinRange(hist, binRange):
    """ Sum bin contents over the bin range """
    return sum( hist.GetBinContent(i) for i in binRange )
def sumW2BinRange(hist, binRange):
    """ Sum bin w2 over the bin range """
    sumw2 = hist.GetSumw2()
    if sumw2.GetSize() == 0:
        raise AssertionError("Asked for sumw2 for a histogram that doesn't have weights")
    return sum( sumw2.At(i) for i in binRange )

def addOverflow(hist, edgeBin, isLower):
    """ Add contents of bins outside range (below or above edgeBin, depending on isLower) to edgeBin """
    if isLower:
        rng_out = range(0, edgeBin)
    else:
        rng_out = range(edgeBin+1, hist.GetNbinsX()+2)
    rng_inc = chain((edgeBin,), iter(rng_out))
    hasSumw2 = ( hist.GetSumw2N() != 0 )
    hist.SetBinContent(edgeBin, sumBinRange(hist, iter(rng_inc)))
    if hasSumw2:
        hist.SetBinError(edgeBin, np.sqrt(sumW2BinRange(hist, iter(rng_inc))))
    for ib in iter(rng_out):
        hist.SetBinContent(ib, 0)
        if hasSumw2:
            hist.SetBinError(ib, 0.)

def histoWithErrors(hist, newErrors):
    """ make a histogram with bin errors set to the given values """
    newHist = cloneHist(hist)
    for i,ierr in zip(count(1), newErrors):
        newHist.SetBinError(i, ierr)
    return newHist

def histoWithErrorsQuadAdded(hist, newErrors):
    """ make a histogram with given values added in quadrature to the existing bin errors """
    newHist = cloneHist(hist)
    for i,ierr in zip(count(1), newErrors):
        newHist.SetBinError(i, np.sqrt(hist.GetBinError(i)**2 + ierr**2))
    return newHist

def histoDivByValues(absHisto):
    """ make a histogram with values 1 and errors err/val """
    relHisto = cloneHist(absHisto)
    from mplbplot.decorators import bins
    for i,b in zip(count(1), bins(absHisto)):
        relHisto.SetBinContent(i, 1.)
        if b.content != 0.:
            relHisto.SetBinError(i, b.error/b.content)
        else:
            relHisto.SetBinError(i, 1.)
    return relHisto

def divide(num, denom):
    """ get the ratio between expected and observed

    Takes into account only statistical uncertainties, using an asymmetric gaussian approximation
    Returns x, y, yerr (numpy arrays with shapes (N,), (N,) and (2,N), where N is the number of bins)
    """
    try:
        cloneHist(num).Divide(num, denom) ## just to force a TH1::CheckConsistency call
    except:
        raise ValueError("Histograms seem to be incompatible")
    from mplbplot.decorators import bins
    vals = np.array([ ( [ nb.xCenter, nb.content/db.content
                      , np.sqrt( (nb.lowError**2*db.content**2 + db.lowError*nb.content**2) ) / db.content**2
                      , np.sqrt( (nb.upError**2 *db.content**2 + db.upError *nb.content**2) ) / db.content**2
                      ] if db.content != 0. else [ nb.xCenter, 1., 1., 1. ] )
                      for nb, db in zip(bins(num), bins(denom)) ])
    return vals[:,0], vals[:,1], vals[:,2:].T
