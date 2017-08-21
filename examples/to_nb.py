#!/usr/bin/env python2
"""
Simple helper script to convert a simple python script with comments to an ipython notebook

see samplenbsrc.py for an example. Generate notebooks can be opened in Jupyter,
"Run all cells" & "Save" should be sufficient to also generate the output nodes.
"""
import tokenize
import itertools

BLOCKTYPES = ["code", "markdown"]
INTERNAL_BLOCKTYPES = [ "multilinestring" ]

KERNELS = {
      "SWAN_python2" : {
          "display_name": "Python 2",
          "language": "python",
          "name": "python2"
        }
    }

def block_out(blkType, blkLines):
    lineMap = lambda ln : ln
    ## strip off 
    if blkType == "markdown":
        lineMap = lambda ln : ln.lstrip("# ")
    elif blkType == "code":
        ## only change the magic ones
        lineMap = lambda ln : ln.lstrip("# ") if ln.startswith("#") and ln.lstrip("# ").strip().startswith("%") else ln
    blkContent = "".join(itertools.imap(lineMap, blkLines)).strip("\n")
    ## interpret a string as multiple comment lines
    if blkType == "multilinestring":
        blkContent = blkContent.strip('"').strip("\n")
        blkType = "markdown"
    return blkType, blkContent

def splitInBlocks(tokens):
    """
    Generate blocks from a tokenize token stream
    """
    lastTok = (None, "", (-1,-1), (-1,-1), "")
    currentBlockType = None
    currentBlockLines = []
    depth_parsqbrbrace = 0
    for tok in tokens:
        (tkTyp, tkString, tkStart, tkEnd, tkLn) = tok
        if tkTyp == tokenize.OP and tkString in ("(", "[", "{"):
            depth_parsqbrbrace += 1
        if tkTyp == tokenize.OP and tkString in (")", "]", "}"):
            depth_parsqbrbrace -= 1

        if len(tkString) > 0: ## skip indent/dedent tokens, they mess up the logical line part
            if tkLn != lastTok[4]: ## new logical line, add, and possibly also finish the block
                if tkStart[0] == lastTok[2][0] and tkLn.startswith(lastTok[4]):
                    currentBlockLines[-1] = tkLn
                elif tkLn.strip() == '"""':
                    pass
                else: ## the generic case
                    if tkTyp == tokenize.COMMENT and not tkString.lstrip("#").strip().startswith("%"):
                        lnType = "markdown"
                    elif tkTyp == tokenize.STRING and depth_parsqbrbrace == 0:
                        lnType = "multilinestring"
                    else:
                        lnType = "code"

                    if lnType != currentBlockType:
                        blkType, blkContent = block_out(currentBlockType, currentBlockLines)
                        if len(blkContent.strip()) > 0:
                            yield blkType, blkContent
                        currentBlockLines = []
                        currentBlockType = lnType

                    currentBlockLines.append(tkLn)

            lastTok = tok

    blkType, blkContent = block_out(currentBlockType, currentBlockLines)
    if len(blkContent.strip()) > 0:
        yield blkType, blkContent

def convertToNotebook(srcName, nbName, kernelspec=None):
    import nbformat
    nb = nbformat.v4.new_notebook()
    if kernelspec:
        if kernelspec not in KERNELS:
            raise ValueError("Unknown kernel '{}'".format(kernelspec))
        else:
            nb.metadata.kernelspec = KERNELS[kernelspec]
    with open(srcName, "r") as srcFile:
        for blkTp, blkSrc in splitInBlocks(tokenize.generate_tokens(srcFile.readline)):
            if blkTp == "code":
                nb.cells.append(nbformat.v4.new_code_cell(source=blkSrc))
            elif blkTp == "markdown":
                nb.cells.append(nbformat.v4.new_markdown_cell(source=blkSrc))
    with open(nbName, "w") as outFile:
        nbformat.write(nb, outFile)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert commented python code to a Jupyter notebook")
    parser.add_argument("sourcefiles", metavar="FILE", nargs="+", help="input source files")
    parser.add_argument("--outdir", nargs="?", help="output directory")
    parser.add_argument("--kernel", nargs="?", help="kernel")
    args = parser.parse_args()

    import os.path
    for inFile in args.sourcefiles:
        if not inFile.endswith(".py"):
            print("Input file names should end with '.py'")
        else:
            if args.outdir:
                outName = os.path.join(args.outdir, "".join((os.path.basename(inFile)[:-3], ".ipynb")))
            else:
                outName = "".join((inFile[:-3], ".ipynb"))
            convertToNotebook(inFile, outName, kernelspec=args.kernel)
