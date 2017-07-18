from setuptools import setup, find_packages

setup(
    name = 'bliss-sle',
    version = '0.1.0',
    packages = find_packages(exclude=['tests']),
    author = 'BLISS-Core Development Team',
    author_email = 'bliss@jpl.nasa.gov',

    namespace_packages = ['bliss'],

    install_requires = [
        'bliss-core==0.19.1'
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
)
