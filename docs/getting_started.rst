..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

.. currentmodule:: hepcrawl


Getting started
===============

About HEPcrawl
--------------

HEPcrawl is a `Scrapy
<https://scrapy.org/>`_ based crawler and acts as the service
responsible for harvesting High-Energy Physics contents for INSPIRE-HEP. HEPcrawl
is periodically triggered by INSPIRE to perform harvesting from sources and HEPcrawl
then pushes JSON records back to INSPIRE ingestion workflows.


Installing HEPcrawl
-------------------

Quick Installation
******************

HEPcrawl can be installed simply just following the next command:

.. code-block:: console

    pip install hepcrawl


.. warning::

    Beware that you may need to install additional system level packages like:
    ``libffi``, ``libssl``, ``libxslt``, ``libxml2``.


Installation for developers
***************************

HEPcrawl can be installed for development in two different ways, Docker and Native installation.

.. note::

    It is highly recommended to install HEPcrawl with Docker since it's
    functional tests are using **only** Docker environment.


.. include:: ./docker_installation.rst

.. include:: ./native_installation.rst

- We are done! Now we have installed HEPcrawl project successfully in development mode.


Run a crawler
-------------

Thanks to the command line tools provided by `Scrapy
<https://scrapy.org/>`_, we can easily run the
spiders as we are developing them. Here is an example using the simple sample spider:

.. code-block:: console

    $ cd ~/repos/hepcrawl
    $ workon hepcrawl_venv
    (hepcrawl_venv)$ scrapy crawl arXiv \\
    -a source_file=file://`pwd`/tests/unit/responses/arxiv/sample_arxiv_record.xml


Run the crawler with INSPIRE (assuming you already have a virtualenv with everything set up).

The example below shows how to get all papers from the 24th June 2016 to the 26th June 2016 from
arXiv where the subject area is ``hep-th`` (HEP Theory). We use the arXiv spider and assign the
article workflow.

.. code-block:: console

    $ cd ~/repos/inspire-next
    $ workon inspire-next_venv
    (inspire-next_venv)$ inspirehep oaiharvester harvest \\
        -m arXiv \\
        -u http://export.arxiv.org/oai2 \\
        -f 2016-06-24 -t 2016-06-26 \\
        -s 'physics:hep-th'
        -a 'spider=arXiv' \\
        -a 'workflow=article'
