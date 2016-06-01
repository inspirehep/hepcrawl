# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Scrapy project for feeds into INSPIRE-HEP (http://inspirehep.net)."""

import os
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

readme = open('README.rst').read()
history = open('CHANGES.rst').read()

requirements = [
    'Scrapy>=1.0.3',
    'scrapyd>=1.1.0',
    'scrapyd-client>=1.0.1',
    'six>=1.9.0',
    'HarvestingKit>=0.6.3',
    'requests>=2.8.1',
    'celery>=3.1.23',
]

test_requirements = [
    'coverage>=4.0.0',
    'pytest>=2.8.0',
    'pytest-cov>=2.1.0',
    'pytest-pep8>=1.0.6',
    'responses>=0.5.0'
]


class PyTest(TestCommand):

    """PyTest Test."""

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        """Init pytest."""
        TestCommand.initialize_options(self)
        self.pytest_args = []
        try:
            from ConfigParser import ConfigParser
        except ImportError:
            from configparser import ConfigParser
        config = ConfigParser()
        config.read('pytest.ini')
        self.pytest_args = config.get('pytest', 'addopts').split(' ')

    def finalize_options(self):
        """Finalize pytest."""
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """Run tests."""
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join('hepcrawl', 'version.py'), 'rt') as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='hepcrawl',
    version=version,
    packages=find_packages(),
    description=__doc__,
    long_description=readme + '\n\n' + history,
    url='https://github.com/inspirehep/hepcrawl',
    author="CERN",
    author_email='admin@inspirehep.net',
    entry_points={'scrapy': ['settings = hepcrawl.settings']},
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=requirements,
    extras_require={
        'docs': [
            'Sphinx>=1.3',
            'sphinx_rtd_theme>=0.1.7',
            'Sphinx-PyPI-upload>=0.2.1',
        ],
        'tests': test_requirements,
        'sentry': [
            'raven==5.1.1',
            'scrapy-sentry',
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    tests_require=test_requirements,
    cmdclass={'test': PyTest},
)
