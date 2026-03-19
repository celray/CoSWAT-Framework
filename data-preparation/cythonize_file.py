#!/bin/python3

'''
this script fetches cython files in QSWAT+ and compiles them

Author  : Celray James CHAWANDA
Email   : celray.chawanda@outlook.com
Licence : All rights Reserved
Repo    : https://github.com/celray

Date    : 2023-12-07 - 10:33
'''

# imports
from cjfx import *

from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize([
            "/drive/d1/github/swat-tools/CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/polygonizeInC.pyx",
            "/drive/d1/github/swat-tools/CoSWAT-Global-Model/data-preparation/resources/QSWATPlus/polygonizeInC2.pyx",
    ]),
    include_dirs=[numpy.get_include()]
)








print()
