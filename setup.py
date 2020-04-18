""" Setuptools-based setup module for mplbplot

derived from the pypa example, see https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mplbplot",

    version="0.2.0",

    description="Simple drawing of ROOT objects with matplotlib",
    long_description=long_description,

    url="https://github.com/pieterdavid/mplbplot",

    author="Pieter David",
    author_email="pieter.david@gmail.com",

    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: Python Modules',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],

    keywords='ROOT matplotlib',

    packages=["mplbplot", "plotit"],

    install_requires=["future", "matplotlib"],

    extras_require={},

    package_data={},
    data_files=[],

    entry_points={},
)
