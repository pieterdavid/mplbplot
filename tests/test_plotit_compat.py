import pytest
import yaml
import os, os.path
import plotit_configuration
import image_utils
import logging
logger = logging.getLogger(__name__)

## Use Agg backend on travis
import matplotlib as mpl
if os.environ.get('DISPLAY','') == '':
    mpl.use('Agg')

testPlotItDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "plotit"))

default_threshold = .995

@pytest.fixture(scope="session")
def plotit_test_inputs(tmpdir_factory):
    workdir = str(tmpdir_factory.mktemp("plotIt"))
    import shutil
    shutil.copytree(os.path.join(testPlotItDir, "files"), os.path.join(workdir, "files"))
    macroPath = os.path.join(testPlotItDir, "generate_files.C")
    import subprocess
    subprocess.check_call(["root", "-l", "-b", "-q", macroPath], cwd=workdir)
    return workdir

def compareToGolden(testImage, goldenName):
    goldenImage = os.path.join(testPlotItDir, "golden", goldenName)
    from image_utils import get_images_likelihood
    return get_images_likelihood(testImage, goldenImage)

def saveConfigAndRun(configuration, workdir, name):
    cfgNm = os.path.join(workdir, "{0}.yml".format(name))
    with open(cfgNm, "w") as cfgF:
        yaml.dump(configuration, cfgF)
    ## emulate plotIt
    from plotit.plotit import plotItFromYAML
    plotItFromYAML(cfgNm, histodir=workdir, outdir=workdir)
    plotNm, plotCfg = next((pNm, pCfg) for pNm, pCfg in configuration["plots"].items())
    logy = plotCfg.get("log-y", "false")
    suffixes = ["", "_logy"] if logy.lower() == "both" else (["_logy"] if logy.lower() == "true" else [""])
    for ext in plotCfg["save-extensions"]:
        for suff in suffixes:
            fName = os.path.join(workdir, "{0}{1}.{2}".format(plotNm, suff, ext))
            if os.path.exists(fName):
                os.rename(fName, os.path.join(workdir, "{0}{1}.{2}".format(name, suff, ext)))
            else:
                logger.warning("Expected file {0} not found".format(fName))

def test_default_no_ratio(plotit_test_inputs):
    configuration = plotit_configuration.get_configuration()
    configuration['plots']['histo1']['show-ratio'] = False
    saveConfigAndRun(configuration, plotit_test_inputs, "default_no_ratio")
    #assert compareToGolden(os.path.join(plotit_test_inputs, "histo1.pdf"), "default_configuration_no_ratio.pdf") > default_threshold

def test_default_ratio(plotit_test_inputs):
    configuration = plotit_configuration.get_configuration()
    configuration['plots']['histo1']['show-ratio'] = True
    saveConfigAndRun(configuration, plotit_test_inputs, "default_ratio")
    #assert compareToGolden(os.path.join(plotit_test_inputs, "histo1.pdf"), "default_configuration_ratio.pdf") > default_threshold

def test_extra_group(plotit_test_inputs):
    configuration = plotit_configuration.get_configuration()
    configuration['plots']['histo1']['show-ratio'] = False
    configuration["groups"] = {"mygroup": {"fill-color": "#CC333F"}}
    saveConfigAndRun(configuration, plotit_test_inputs, "extra_group")
    #assert compareToGolden(os.path.join(plotit_test_inputs, "histo1.pdf"), "default_configuration_no_ratio.pdf") > default_threshold
