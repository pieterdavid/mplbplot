"""
Simple tests for mplbplot.decorators
"""
__author__ = "Pieter David <pieter.david@gmail.com>"

if __name__ == "__main__":
    import ROOT
    from mplbplot.decorators import bins, points

    print "1D histogram"
    h = ROOT.TH1F("hTest", "Test histogram", 10, -5., 5.)
    h.FillRandom("gaus", 250)
    for b in bins(h):
        print "In [ {l:.2f} , {u:.2f} [  :  {v:.2f} +/- {e:.2f}".format(l=b.xLowEdge, u=b.xUpEdge, v=b.content, e=b.error)

    print "Graph without errors"
    g = ROOT.TGraph(h)
    for p in points(g):
        print "( {x:.2f} +/- {xe:.2f} , {y:.2f} +/- {ye:.2f} )".format(x=p.x, xe=p.xError, y=p.y, ye=p.yError)
    print "Graph with errors"
    ge = ROOT.TGraphErrors(h)
    for p in points(ge):
        print "( {x:.2f} +/- {xe:.2f} , {y:.2f} +/- {ye:.2f} )".format(x=p.x, xe=p.xError, y=p.y, ye=p.yError)

    f2 = ROOT.TF2("f2", "TMath::Gaus(x, 0., 1.)*TMath::Gaus(y, 0., 1.)", -10., 10., -10., 10.)
    h2 = ROOT.TH2F("hOtherTest", "two-dimensional test histo", 10, -5., 5., 5, -2.5, 2.5)
    h2.FillRandom("f2", 2500)
    for b in bins(h2):
        print "In [ {xl:.2f} , {xu:.2f} [ x [ {yl:.2f} , {yu:.2f} ]  :  {v:.2f} +/- {e:.2f}".format(xl=b.xLowEdge, xu=b.xUpEdge, yl=b.yLowEdge, yu=b.yUpEdge, v=b.content, e=b.error)
