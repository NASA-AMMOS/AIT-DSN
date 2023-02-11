# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import io
from os import path, listdir
from setuptools import setup, find_packages

description = "AIT DSN provides APIs for connecting to the Deep Space Network (DSN) " \
              "via the Space Link Extension interfaces."

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with io.open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name = 'ait-dsn',
    version = '3.0.0+snr',
    description  = description,
    long_description = long_description,
    long_description_content_type = 'text/x-rst',
    url = 'https://github.com/NASA-AMMOS/AIT-DSN',
    packages = find_packages(exclude=['tests']),
    author = 'AIT Development Team',
    author_email='ait-pmc@googlegroups.com',

    namespace_packages = ['ait'],

    install_requires = [
        'greenlet==0.4.16',
        'pyasn1',
        'bitstring',
        'graphviz',
    ],

    extras_require = {
        'docs':  [
            'Sphinx',
            'sphinx_rtd_theme',
            'sphinxcontrib-httpdomain'
        ],
        'tests': [
            'nose',
            'coverage',
            'mock',
            'pylint'
        ],
    },

    entry_points = {
        'console_scripts': [
            '{}=ait.dsn.bin.{}:main'.format(
                f.split('.')[0].replace('_', '-'),
                f.split('.')[0])
            for f in listdir('./ait/dsn/bin')
            if f.endswith('.py') and
            f != '__init__.py' and
            'ait' in f

        ]
    }
)
