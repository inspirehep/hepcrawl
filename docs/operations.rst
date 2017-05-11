..
    This file is part of hepcrawl.
    Copyright (C) 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Deployment
==========

Traditionally, deployment of `scrapy` projects are done using `scrapyd`_ package. This adds a HTTP API on top
of `scrapy` to allow for adding/removing Scrapy projects and most importantly; scheduling crawls.

The easiest way to setup scrapy is to login on a machine, fork the `hepcrawl`_ repository, install it,
and use ``scrapyd-deploy`` command from ``scrapyd-client`` package to push the project to Scrapyd.


Install HEPCrawl
----------------

We will start with creating a Python virtual environment to install our packages:


.. code-block:: console

    mkvirtualenv hepcrawl
    cdvirtualenv
    mkdir src && cd src


Then proceed to install HEPCrawl on a remote server by cloning the sources.

.. code-block:: console

    $ git clone https://github.com/inspirehep/hepcrawl.git
    $ cd hepcrawl
    $ pip install .


This should install all dependencies, including Scrapyd.

Setup Scrapyd
-------------

Next, it is important that you setup your ``/etc/scrapyd/scrapyd.conf`` file with correct paths
in order for Scrapyd to store internal dbs, items, logs etc.

For example:

.. code-block:: text

    [scrapyd]
    eggs_dir    = /opt/hepcrawl/var/eggs
    logs_dir    = /opt/hepcrawl/var/logs
    items_dir   = /opt/hepcrawl/var/items
    dbs_dir     = /opt/hepcrawl/var/dbs


See `Scrapyd-documentation`_ for more config options.


Run Scrapyd
-----------

Now you can run the Scrapyd server in a separate terminal:

.. code-block:: console

    (hepcrawl)$ scrapyd


Scrapyd runs by default on port 6800. You can for example setup an webserver proxy (e.g. with nginx or apache). In addition, we recommend using a task-runner like ``supervisord`` to run the command as a daemon.


Deploy Scrapy project
---------------------

To deploy the HEPcrawl project, simply enter the source folder and run `scrapyd-deploy`.

.. code-block:: console

    (hepcrawl)$ cdvirtualenv src/hepcrawl
    (hepcrawl)$ scrapyd-deploy    # assumes a Scrapy server running on port 6800


This reads the configuration `scrapy.cfg` to deploy and by default the configuration should be correct.


Schedule crawls
---------------

Schedule crawls using e.g. curl (or via the `inspire-crawler`_ package):

.. code-block:: console

    $ curl http://crawler.example.org:6800/schedule.json -d project=hepcrawl -d spider=WSP


Pushing to remote servers
-------------------------

You can also choose to push the scrapyd project to a remote server. For this to work
you need to edit the ``scrapy.cfg`` in your Scrapy project sources and add your
remote server information:

.. code-block:: text

    [deploy:myserver]
    url = http://crawler.example.org
    project = hepcrawl
    #username = scrapy
    #password = secret


Finally deploy the egg of hepcrawl to the remote server:

.. code-block:: console

    $ scrapyd-deploy myserver



Install via PyPi
----------------

You can also install ``hepcrawl`` from PyPi and use ``pip`` to install the package (preferably in a virtual environment):

.. code-block:: console

    (hepcrawl)$ pip install hepcrawl

This will install all dependencies, including ``scrapyd``.


Enable Sentry
-------------

To enable sentry you need to install some packages:

.. code-block:: console

    pip install -e .[sentry]


And then add to your environment the variable ``APP_SENTRY_DSN`` with the connection information.

.. code-block:: console

    APP_SENTRY_DSN="https://foo:bar@sentry.example.com/1" scrapyd


.. note::

    If you have setup `supervisord` you can use the ``environment`` config option to add variables.



Known issues
============

Sentry integration with Python 2.7.9
------------------------------------

You need to install our fork of Raven:

.. code-block:: console

    pip install git+https://github.com/inspirehep/raven-python@master#egg=raven-python==5.1.1.dev20160118


.. _hepcrawl: https://github.com/inspirehep/hepcrawl
.. _scrapyd: http://scrapyd.readthedocs.io/
.. _Scrapyd-documentation: http://scrapyd.readthedocs.io/en/latest/config.html?highlight=database#configuration-file
.. _inspire-crawler: http://pythonhosted.org/inspire-crawler
