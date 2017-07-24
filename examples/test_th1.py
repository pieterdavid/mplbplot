"""
Simple tests for draw_th1
"""
__author__ = "Pieter David <pieter.david@gmail.com>"

## TODO make a notebook out of this?

if __name__ == "__main__":
    import ROOT
    from ROOT import TH1F, TCanvas
    from matplotlib import pyplot as plt
    import mplbplot.decorateAxes ## object-oriented API
    import matplotlib.ticker

    ## TEST hist
    h1 = TH1F("aHisto", "A histogram", 20, -5., 5.)
    h1.FillRandom("gaus", 250)
    h1.SetLineColor(ROOT.kRed)
    c1 = TCanvas("c1", "First canvas")
    h1.GetXaxis().SetRangeUser(-5.,5.)
    h1.Draw("HIST")
    fig,ax = plt.subplots(num="Fig1")
    ax.rhist(h1, histtype="step", color="r", volume=True)
    ax.set_xlim(-5.,5.)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=1.0))
    ax.tick_params(direction="out", top="off", right="off")

    ## now a stack
    h2 = TH1F("anotherHisto", "Another histogram", 20, -5., 5.)
    h2.FillRandom("gaus", 100)
    from ROOT import THStack
    st = THStack("aStack", "Stacked histograms")
    st.Add(h1, "H")
    st.Add(h2, "H")
    c2 = TCanvas("c2", "First canvas")
    st.Draw()
    fig,ax = plt.subplots(num="Fig2")
    ax.rhist([h1,h2], histtype="step", color=["r", "k"], stacked=True, volume=True)
    ax.set_xlim(-5.,5.)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=1.0))
    ax.tick_params(direction="out", top="off", right="off")

    h3 = TH1F("thirdHisto", "A histogram", 20, -5., 5.)
    h3.FillRandom("gaus", 250)
    h3.SetLineColor(ROOT.kRed)
    h3.SetMarkerStyle(ROOT.kCircle)
    c3 = TCanvas("c3", "Third canvas")
    h3.GetXaxis().SetRangeUser(-5.,5.)
    h3.Draw("PL")
    fig,ax = plt.subplots(num="Fig3")
    ax.rplot(h3, "ro-", empty=True)
    ax.set_xlim(-5.,5.)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=1.0))
    ax.tick_params(direction="out", top="off", right="off")

    h4 = TH1F("fourthHisto", "A histogram", 20, -5., 5.)
    h4.FillRandom("gaus", 250)
    h4.SetLineColor(ROOT.kRed)
    h4.SetMarkerStyle(ROOT.kCircle)
    c4 = TCanvas("c4", "Fourth canvas")
    h4.GetXaxis().SetRangeUser(-5.,5.)
    h4.Draw("E2")
    fig,ax = plt.subplots(num="Fig4")
    ax.rerrorbar(h4, kind="box", color="red", alpha=.3, empty=True)
    ax.rerrorbar(h4, fmt="ro", kind="bar", empty=True)
    ax.set_xlim(-5.,5.)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=1.0))
    ax.tick_params(direction="out", top="off", right="off")

    # TODO: add tests for error band and text option

    plt.show()
