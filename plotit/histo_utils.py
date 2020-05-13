"""
Utility functions to manipulate ROOT histograms (for overflow display and systematics)
"""
__all__ = ("cloneHist", "addOverflow", "divide")

from builtins import zip, range
from itertools import count, chain
import math
import numpy as np

from . import logger

from cppyy import gbl
gbl.TH1.AddDirectory(False)

def cloneHist(hist, newName=None):
    if gbl.TH1.AddDirectoryStatus():
        raise AssertionError("Cannot clone histograms as free objects when TH1::AddDirectoryStatus is True")
    return ( hist.Clone(newName) if newName else hist.Clone() )

def hasSumw2(hist):
    return hist.GetSumw2() and hist.GetSumw2N()

def addOverflow(hist, edgeBin, isLower):
    """ Add contents of bins outside range (below or above edgeBin, depending on isLower) to edgeBin """
    if isLower:
        rng = slice(0, edgeBin+1)
        rng_out = range(rng.start, edgeBin)
    else:
        rng = slice(edgeBin, hist.GetNbinsX()+2)
        rng_out = range(edgeBin+1, rng.stop)
    contSum = np.sum(tarr_asnumpy(hist)[rng])
    hist.SetBinContent(edgeBin, contSum)
    for ib in iter(rng_out):
        hist.SetBinContent(ib, 0)
    if hasSumw2(hist):
        errSum = np.sum(tarr_asnumpy(hist.GetSumw2())[rng])
        hist.SetBinError(edgeBin, math.sqrt(errSum))
        for ib in iter(rng_out):
            if ib != edgeBin:
                hist.SetBinError(ib, 0.)

def tarr_asnumpy(tarr, shape=None):
    llv = tarr.GetArray()
    arr = np.frombuffer(llv, dtype=llv.typecode, count=tarr.GetSize())
    if shape is not None:
        return np.reshape(arr, shape)
    else:
        return arr

def getShape(hist):
    shape = tuple(getattr(hist, "GetNbins{0}".format(ax))()+2 for __,ax in zip(range(hist.GetDimension()), "XYZ"))
    prod = 1
    for dimn in shape:
        prod *= dimn
    assert prod == hist.GetSize()
    return shape

def h1With(hist, values=None, errors2=None):
    # To replace the above, new convention: under- and overflow bin are included (ROOT numbering)
    if values is None and errors2 is None:
        return hist
    else:
        newHist = cloneHist(hist)
        if errors2 is not None and not hasSumw2(newHist):
            newHist.Sumw2()
        for i in range(0, hist.GetNbinsX()+2):
            if values is not None:
                newHist.SetBinContent(i, values[i])
            if errors2 is not None:
                #newHist.GetSumw2()[i] = errors2[i]
                newHist.SetBinError(i, np.sqrt(errors2[i]))
                ###newHist.SetBinError(i, errors2[i])
    return newHist

def divide(num, denom):
    """ get the ratio between expected and observed

    Takes into account only statistical uncertainties, using an asymmetric gaussian approximation
    Returns x, y, yerr (numpy arrays with shapes (N,), (N,) and (2,N), where N is the number of bins)
    """
    try:
        cloneHist(num).Divide(num, denom) ## just to force a TH1::CheckConsistency call
    except:
        raise ValueError("Histograms seem to be incompatible")
    from mplbplot.decorators import bins ## TODO numpy-vectorize this
    vals = np.array([ ( [ nb.xCenter, nb.content/db.content
                      , np.sqrt( (nb.lowError**2*db.content**2 + db.lowError**2*nb.content**2) ) / db.content**2
                      , np.sqrt( (nb.upError**2 *db.content**2 + db.upError**2 *nb.content**2) ) / db.content**2
                      ] if db.content != 0. else [ nb.xCenter, 1., 1., 1. ] )
                      for nb, db in zip(bins(num), bins(denom)) ])
    return vals[:,0], vals[:,1], vals[:,2:].T
