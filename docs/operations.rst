..
    This file is part of hepcrawl.
    Copyright (C) 2016 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Deployment
==========

To install ``hepcrawl`` on a remote server, you can login to it and use ``pip`` to install the package (preferably in a virtual environment):

.. code-block:: shell

    (hepcrawl)$ pip install hepcrawl


This will install all dependencies, including ``scrapyd`` which we will use for running the HTTP API
to schedule crawls.

It is important that you setup your ``scrapyd.conf`` file with correct paths to internal dbs, items, logs etc.
with the correct permissions.

.. code-block:: text

    [scrapyd]
    eggs_dir    = /opt/hepcrawl/var/eggs
    logs_dir    = /opt/hepcrawl/var/logs
    items_dir   = /opt/hepcrawl/var/items
    dbs_dir     = /opt/hepcrawl/var/dbs


See `Scrapyd-documentation`_ for more config options.

Now you can run:

.. code-block:: shell

    (hepcrawl)$ scrapyd


Scrapyd runs by default on port 6800. You can for example setup an nginx proxy or change the port
in the configuration. In addition, we recommend using a task running like ``supervisord`` to run the command as a daemon.

Next you need to add a project to your instance (only needed once). The easiest is to go on your local
machine, fork the ``hepcrawl`` repository, install it, and use ``scrapyd-deploy`` command from ``scrapyd-client`` package.


.. code-block:: shell

    $ git clone https://github.com/inspirehep/hepcrawl.git
    $ cd hepcrawl
    $ pip install .


Now edit the ``scrapy.cfg`` and add your remote server url:

.. code-block:: text

    [deploy:myserver]
    url = http://crawler.example.org
    project = hepcrawl
    #username = scrapy
    #password = secret


Finally deploy the egg of hepcrawl to the remote server:

.. code-block:: shell

    $ scrapyd-deploy myserver


Schedule crawls using e.g. curl (or via the `inspire-crawler`_ package):

.. code-block:: shell

    $ curl http://crawler.example.org:6800/schedule.json -d project=hepcrawl -d spider=WSP



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


.. _Scrapyd-documentation: http://scrapyd.readthedocs.io/en/latest/config.html?highlight=database#configuration-file
.. _inspire-crawler: http://pythonhosted.org/inspire-crawler
