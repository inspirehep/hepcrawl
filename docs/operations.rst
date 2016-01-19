..
    This file is part of hepcrawl.
    Copyright (C) 2016 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Deployment
==========



Enable Sentry
=============

To enable sentry you need to install some packages:

.. code-block:: shell

    pip install -e .[sentry]


And enable the correct ``EXTENSIONS``:

.. code-block:: python

    EXTENSIONS = {
        'scrapy_sentry.extensions.Errors': 10,
        'hepcrawl.extensions.ErrorHandler': 555,
    }
    SENTRY_DSN = 'YOUR DSN URL'



Known issues
============


Sentry integration with Python 2.7.9
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to install our fork of Raven:

.. code-block:: shell

    pip install git+https://github.com/inspirehep/raven-python@master#egg=raven-python==5.1.1.dev20160118
