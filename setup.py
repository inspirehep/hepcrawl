# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017, 2018 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Scrapy project for feeds into INSPIRE-HEP (http://inspirehep.net)."""

from __future__ import absolute_import, division, print_function

from setuptools import setup, find_packages

readme = open('README.rst').read()

install_requires = [
    'amqp~=2.0,>2.2.0,!=2.3.0',
    'autosemver~=0.2',
    'inspire-schemas~=58.0,>=58.0.0',
    'inspire-dojson~=60.0,>=60.0.3',
    'inspire-utils~=2.0,>=2.0.2',
    'Scrapy>=1.1.0',
    'scrapy-crawl-once~=0.1,>=0.1.1',
    'scrapy-sentry~=0.0,>=0.8.0',
    # TODO: unpin once they support wheel building again
    'scrapyd==1.1.0',
    'scrapyd-client>=1.0.1',
    'six>=1.9.0',
    'requests>=2.8.1',
    'celery~=4.0,>=4.1.0,<4.2.0',
    'redis>=2.10.5',
    'pyasn1>=0.1.8',  # Needed for dependency resolving.
    'LinkHeader>=0.4.3',
    'furl>=0.4.95',
    'ftputil>=3.3.1',
    'python-dateutil~=2.0,>=2.7.0',
    'python-scrapyd-api>=2.0.1',
    'harvestingkit>=0.6.12',
    'Sickle~=0.6,>=0.6.2',
]

tests_require = [
    'check-manifest>=0.25',
    'coverage>=4.0',
    'freezegun>=0.3.9',
    'isort==4.2.2',
    'mock~=2.0,>=2.0.0',
    'pytest>=2.8.0',
    'pytest-cov>=2.1.0',
    'pytest-pep8>=1.0.6',
    'requests-mock>=1.3.0',
    'pydocstyle>=1.0.0',
    'PyYAML',
]

extras_require = {
    'docs': [
        'Sphinx>=1.4',
        'sphinxcontrib-napoleon>=0.6.1',
    ],
    'tests': tests_require,
    'sentry': [
        'raven~=6.0,>=6.2.1',
        'scrapy-sentry',
    ],
}

setup_requires = [
    'autosemver~=0.2',
    'pytest-runner>=2.7.0',
]

extras_require['all'] = []
for name, reqs in extras_require.items():
    extras_require['all'].extend(reqs)


URL = 'https://github.com/inspirehep/hepcrawl'

setup(
    name='hepcrawl',
    packages=find_packages(),
    description=__doc__,
    long_description=readme,
    url=URL,
    author="CERN",
    author_email='admin@inspirehep.net',
    entry_points={'scrapy': ['settings = hepcrawl.settings']},
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    autosemver={
        'bugtracker_url': URL + '/issues/',
    },
    setup_requires=setup_requires,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    package_data={
        'hepcrawl': ['*.cfg'],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Framework :: Scrapy',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
)
