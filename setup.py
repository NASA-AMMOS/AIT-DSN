from setuptools import setup, find_packages
import os

setup(
    name = 'bliss-sle',
    version = '0.1.0',
    packages = find_packages(exclude=['tests']),
    author = 'BLISS-Core Development Team',
    author_email = 'bliss@jpl.nasa.gov',

    namespace_packages = ['bliss'],

    install_requires = [
        'bliss-core==0.23.0',
        'pyasn1'
    ],
    dependency_links = [
       'https://bliss.jpl.nasa.gov/pypi/simple/bliss-core/'
    ],

    extras_require = {
        'docs':  [
            'Sphinx==1.4',
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
            '{}=bliss.sle.bin.{}:main'.format(
                f.split('.')[0].replace('_', '-'),
                f.split('.')[0])
            for f in os.listdir('./bliss/sle/bin')
            if f.endswith('.py') and
            f != '__init__.py' and
            'bliss' in f

        ]
    }
)
