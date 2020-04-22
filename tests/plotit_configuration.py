def conf_get_configuration():
    f = {
            'width': 800,
            'height': 800,
            'luminosity-label': '%1$.2f fb^{-1} (8 TeV)',
            'experiment': "CMS",
            'extra-label': "Preliminary",
            'root': 'files',
            'luminosity': 1,
            'luminosity-error': 0.2,
            'error-fill-style': 3154,
            'error-fill-color': "#ee556270",
            'ratio-fit-error-fill-style': 1001,
            'ratio-fit-error-fill-color': "#aa556270",
            'ratio-fit-line-color': "#0B486B",
            'blinded-range-fill-color': "#29556270",
            'blinded-range-fill-style': 1001
            }

    return {'configuration': f}

def conf_get_plots():
    f = {
            'histo1': {
                'x-axis': "X axis",
                'y-axis': "Y axis",
                'y-axis-format': "%1% / %2$.0f GeV",
                'y-axis-show-zero': True,
                'x-axis-range': [2, 9.5],
                'show-overflow': True,
                'show-ratio': True,
                'normalized': False,
                'fit-ratio': True,
                'rebin': 4,
                'log-y': 'false',
                'save-extensions': ['pdf'],
                'blinded-range': [3, 5.2],
                }
            }

    return {'plots': f}

def conf_get_legend():
    f = {
            'position': [0.25, 0.78, 0.45, 0.9],
            'columns': 2
            }

    return {'legend': f}

def conf_get_files():
    f = {
            'data.root': {'type': 'data', 'legend': 'Data'},
            'MC_sample1.root': {'type': 'mc', 'legend': 'MC 1', 'cross-section': 245.8, 'generated-events': 2167, 'fill-color': '#D95B43', 'order': 1, 'group': 'mygroup'},
            'MC_sample2.root': {'type': 'mc', 'legend': 'MC 2', 'cross-section': 666.3, 'generated-events': 2404, 'fill-color': '#53777A', 'order': 0, 'group': 'mygroup'},
            }

    return {'files': f}

def get_configuration():
    configuration = {}
    configuration.update(conf_get_files())
    configuration.update(conf_get_configuration())
    configuration.update(conf_get_plots())
    configuration.update(conf_get_legend())

    return configuration

