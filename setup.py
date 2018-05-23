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

from setuptools import setup, find_packages
import os

setup(
    name = 'ait-dsn',
    version = '0.1.0',
    packages = find_packages(exclude=['tests']),
    author = 'AIT Development Team',
    author_email = 'ait-dev@googlegroups.com',

    namespace_packages = ['ait'],

    install_requires = [
        'ait-core>=1.0.0',
        'pyasn1',
        'enum34==1.1.6'
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
            for f in os.listdir('./ait/dsn/bin')
            if f.endswith('.py') and
            f != '__init__.py' and
            'ait' in f

        ]
    }
)
