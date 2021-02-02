..
    This file is part of hepcrawl.
    Copyright (C) 2015, 2016, 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.

Installation
============


Quick Installation
------------------


.. code-block:: console

    pip install hepcrawl


.. warning::

    Beware that you may need to install additional system level packages like libffi, libssl, libxslt, libxml2 etc.


.. _local_install:

Installation for developers (not using Docker)
----------------------------------------------

We start by creating a virtual environment for our Python packages:

.. code-block:: console

    mkvirtualenv hepcrawl
    cdvirtualenv
    mkdir src && cd src


Now we grab the code and install it in development mode:

.. code-block:: console

    git clone https://github.com/inspirehep/hepcrawl.git
    cd hepcrawl
    pip install -e .


Development mode ensures that any changes you do to your sources are automatically
taken into account = no need to install again after changing something.

Finally run the tests to make sure all is setup correctly:

.. code-block:: console

    pytest tests/unit

.. warning::

    Unfortunately running functional tests for hepcrawl without Docker is difficult,
    and as such not supported in this documentation. You would have to try and set up
    all of the dummy services that are used for each tests as defined in
    ``docker-compose.test.yml`` yourself locally.


Installation for developers with Docker
---------------------------------------

Grab the code from github, you can optionally follow the above steps to create the
virtual environment, but that is not neccessary – might be helpful if your IDE wants
to install dependencies for suggestions though. See :ref:`local_install`.

Then install the test dependencies inside Docker:

.. code-block:: console

    docker-compose -f docker-compose.deps.2.7.yml run --rm pip

To run the tests (e.g. unit):

.. code-block:: console

    docker-compose -f docker-compose.test.2.7.yml run --rm unit

There are also Python 3 variants ending in ``.3.6.yml`` in case you want to test with Python 3. These are built in a simpler way and require to rebuild the images on every code change with:

.. code-block:: console

    docker-compose -f docker-compose.test.3.6.yml build

Installation for testing with inspire-next in Docker
----------------------------------------------------

Grab the code from github, you can optionally follow the above steps to create the
virtual environment. See :ref:`local_install`.

In ``inspire-next`` in the ``services.yml`` file add a new volume in the static section, it should
look like so now:

.. code-block:: yaml

    static:
      image: busybox
      volumes:
        - "/local/path/to/hepcrawl/repo:/hepcrawl_code"  # <- added
        - ".:/code"


Then in the ``docker-compose.deps.yml`` we need to tell ``scrapyd-deploy`` service to work with
the new code by changing the ``working_dir`` to ``/hepcrawl_code/hepcrawl``:

.. code-block:: yaml

    scrapyd-deploy:
      extends:
        file: services.yml
        service: base
      # working_dir: /virtualenv/lib/python2.7/site-packages/hepcrawl
      working_dir: /hepcrawl_code/hepcrawl
      command: scrapyd-deploy
      volumes_from:
        - static
      links:
        - scrapyd

Last step is to deploy the spiders to `scrapyd` (see more in :doc:`Deployment <operations>`):

.. code-block:: console

    cd /path/to/inspire-next
    docker-compose kill scrapyd static
    docker-compose rm scrapyd static
    docker-compose -f docker-compose.deps.yml run --rm scrapyd-deploy

You will need to deploy your spiders to `scrapyd` after every change to the code.


Run a crawler
-------------

Locally through scrapy
++++++++++++++++++++++

Thanks to the command line tools provided by Scrapy, we can easily test the
spiders as we are developing them. Here is an example using the simple sample
spider. You may need to allow access to the path where scrapy stores it's files first:

.. code-block:: console

    sudo chown $(whoami) -R /var/lib/scrapy
    chmod +w -R /var/lib/scrapy

    cdvirtualenv src/hepcrawl
    scrapy crawl arXiv_single \
        -a identifier=oai:arXiv.org:1801.00009 \
        -t jl -o /tmp/output.jl

This will save the crawled record in a file ``/tmp/output.jl`` as JSON-lines format.


Through inspire-next
++++++++++++++++++++

Run the crawler with INSPIRE (assuming you already have a virtualenv with everything set up).

The example below shows how to get all papers from the 24th June 2016 to the 26th June 2016
from arXiv where the subject area is hep-th (HEP Theory). We use the arXiv spider and assign the
article workflow.

.. code-block:: console

    workon inspire-next
    inspirehep crawler schedule arXiv article \
        --kwarg 'from_date=2016-06-24' \
        --kwarg 'until_date=2016-06-26' \
        --kwarg 'sets=physics:hep-th'

Or if you're running Docker:

.. code-block:: console

    local$ docker-compose run --rm web bash
    docker$ inspirehep crawler schedule arXiv article \
        --kwarg 'from_date=2016-06-24' \
        --kwarg 'until_date=2016-06-26' \
        --kwarg 'sets=physics:hep-th'

You should see the workflows appearing in the holdingpen: http://localhost:5000/holdingpen.

Thanks for contributing!
