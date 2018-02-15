..
    This file is part of hepcrawl.
    Copyright (C) 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.


Native installation
+++++++++++++++++++

System prerequisites
####################

This guide expects you to have installed in your system the following tools:

* ``git``,
* ``virtualenv``,
* ``virtualenvwrapper``,
* ``libffi``
* ``libssl``,
* ``libxslt``,
* ``libxml2``


Create a virtual environment
############################

Create a virtual environment and clone the HEPcrawl source code using `git`:

.. code-block:: console

    $ mkdir -p ~/repos
    $ cd ~/repos
    $ git clone https://github.com/inspirehep/hepcrawl.git
    $ mkvirtualenv --python=python2.7 hepcrawl_venv
    $ workon hepcrawl_venv
    (hepcrawl_venv)$ cd hepcrawl

.. note::

    It is better to clone the project into a folder of your choice and not in a folder
    inside virtualenv. This approach enables you to switch to a new virtual environment
    without having to clone the project again. You simply specify on
    which environment you want to ``workon`` using its name.

Install requirements
####################
- Use `pip` to install all requirements in development mode, it's recommended to upgrade pip and
  setuptools to latest too:

.. code-block:: console

    (hepcrawl_venv)$ workon hepcrawl_venv
    (hepcrawl_venv)$ cd ~/repos/hepcrawl
    (hepcrawl_venv)$ pip install --upgrade pip setuptools
    (hepcrawl_venv)$ pip install -e .[all]

.. note::
    Development mode ensures that any changes you do to your sources are automatically
    taken into account, that means that there is no need to install again after changing something.

- Finally run the ``unit`` tests to make sure all is setup correctly:

.. code-block:: console

    py.tests tests/unit -vv
