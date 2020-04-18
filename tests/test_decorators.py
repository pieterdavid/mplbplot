from __future__ import print_function

import pytest

@pytest.fixture(scope="module")
def h1():
    from cppyy import gbl
    h = gbl.TH1F("hTest", "Test histogram", 10, -5., 5.)
    h.FillRandom("gaus", 250)
    yield h

@pytest.fixture(scope="module")
def h2():
    from cppyy import gbl
    f2 = gbl.TF2("f2", "TMath::Gaus(x, 0., 1.)*TMath::Gaus(y, 0., 1.)", -10., 10., -10., 10.)
    h2 = gbl.TH2F("hOtherTest", "two-dimensional test histo", 10, -5., 5., 5, -2.5, 2.5)
    h2.FillRandom("f2", 2500)
    yield h2

def test_bins1(h1):
    from mplbplot.decorators import bins
    for b in bins(h1):
        print("In [ {l:.2f} , {u:.2f} [  :  {v:.2f} +/- {e:.2f}".format(l=b.xLowEdge, u=b.xUpEdge, v=b.content, e=b.error))

def test_points(h1):
    from cppyy import gbl
    g = gbl.TGraph(h1)
    from mplbplot.decorators import points
    for p in points(g):
        print("( {x:.2f} +/- {xe:.2f} , {y:.2f} +/- {ye:.2f} )".format(x=p.x, xe=p.xError, y=p.y, ye=p.yError))

def test_points_errors(h1):
    from cppyy import gbl
    ge = gbl.TGraphErrors(h1)
    from mplbplot.decorators import points
    for p in points(ge):
        print("( {x:.2f} +/- {xe:.2f} , {y:.2f} +/- {ye:.2f} )".format(x=p.x, xe=p.xError, y=p.y, ye=p.yError))

def test_bins2(h2):
    from mplbplot.decorators import bins
    for b in bins(h2):
        print("In [ {xl:.2f} , {xu:.2f} [ x [ {yl:.2f} , {yu:.2f} ]  :  {v:.2f} +/- {e:.2f}".format(xl=b.xLowEdge, xu=b.xUpEdge, yl=b.yLowEdge, yu=b.yUpEdge, v=b.content, e=b.error))
