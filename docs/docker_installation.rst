..
    This file is part of hepcrawl.
    Copyright (C) 2017 CERN.

    hepcrawl is a free software; you can redistribute it and/or modify it
    under the terms of the Revised BSD License; see LICENSE file for
    more details.


Docker installation
+++++++++++++++++++


Docker (Linux)
##############

Docker is an application that makes it simple and easy to run processes in a container,
which are like virtual machines, but more resource-friendly. For a detailed introduction to the
different components of a Docker container. For a detailed introduction to the different components
of a Docker container, you can follow `this tutorial
<https://www.digitalocean.com/community/tutorials/the-docker-ecosystem-an-introduction-to-common-components>`_.


HEPcrawl and Docker
###################

Get the latest Docker appropriate to your operation system, by visiting `Docker's official web site <https://www.docker.com/>`_ and accessing the
*Get Docker* section.

.. note:: If you are using Mac, please build a simple box with ``docker-engine`` above ``1.10`` and
         ``docker-compose`` above ``1.6.0``.

Make sure you can run docker without ``sudo``.

- ``id $USER``

  If you are not in the ``docker`` group, run the following command and then restart ``docker``. If this doesn't work, just restart your machine :)

- ``newgrp docker`` or ``su - $USER``

- ``sudo usermod -a -G docker $USER``

Get the latest `docker-compose
<https://docs.docker.com/compose/>`_:

.. code-block:: console

   $ sudo pip install docker-compose

- Add ``DOCKER_DATA`` env variable in your ``.bashrc`` or ``.zshrc``. In this directory you will have all the persistent data between Docker runs.

.. code-block:: console

   $ export DOCKER_DATA=~/hepcrawl_docker_data/
   $ mkdir -p "$DOCKER_DATA"

By default the virtualenv of HEPcrawl project in docker is under ``${DOCKER_DATA}/tmp/hepcrawl_venv`` directory. In
order to be available the ``DOCKER_DATA`` env variable immediately we have to execute the following command
otherwise it will be available only until the next reboot.

.. code-block:: console

   $ source ~/.bashrc

or

.. code-block:: console

   $ source ~/.zshrc

- Install a host persistent virtual environment

.. Note::

 From now on all the docker-compose commands must be run at the root of the
 hepcrawl repository, you can get a local copy with:

.. code-block:: console

   $ git clone git://github.com/inspirehep/hepcrawl
   $ cd hepcrawl

.. code-block:: console

   $ docker-compose -f docker-compose.deps.yml run --rm pip

.. note:: If you have trouble with internet connection inside docker probably you are facing known
          DNS issue. Please follow `this solution
          <http://askubuntu.com/questions/475764/docker-io-dns-doesnt-work-its-trying-to-use-8-8-8-8/790778#790778>`_
          with DNS: ``--dns 137.138.17.5 --dns 137.138.16.5``.

- Deploy your code to ``scrapyd`` container:

.. code-block:: console

   $ docker-compose -f docker-compose.test.yml run --rm scrapyd_deploy

- Run tests in an **isolated** environment.

.. Note::

 The tests use a different set of containers, so if you run both at the same time you might
 start having ram/load issues, if so, you can stop all the containers using
 ``docker-compose kill -f`` command.

You can choose one of the following tests types:

  - unit
  - functional_arxiv
  - functional_wsp
  - functional_desy

.. code-block:: console

   $ docker-compose -f docker-compose.test.yml run --rm <tests type>
   $ docker-compose -f docker-compose.test.yml down

.. tip:: - cleanup all the containers:

           ``docker rm $(docker ps -qa)``

         - cleanup all the images:

           ``docker rmi $(docker images -q)``

         - cleanup the virtualenv (careful, if docker_data is set to something you care about, it will be removed):

           ``sudo rm -rf "${DOCKER_DATA}"``


Extra useful tips
#################

- Find container's names from executing ``docker-compose`` file:

.. code-block:: console

   $ docker-compose -f docker-compose.test.yml ps

Normally we will see an output like this:

.. code-block:: console

              Name                       Command          State                Ports
   ------------------------------------------------------------------------------------------------
   hepcrawl_celery_1       /docker_entrypoint.sh cele ...   Up
   hepcrawl_ftp_server_1   /bin/sh -c /run.sh -c 50 - ...   Up      21/tcp, 30000/tcp, 30001/tcp, 30002/tcp, 30003/tcp, 30004/tcp, 30005/tcp, 30006/tcp, 30007/tcp, 30008/tcp, 30009/tcp
   hepcrawl_rabbitmq_1     docker-entrypoint.sh rabbi ...   Up      25672/tcp, 4369/tcp, 5671/tcp, 5672/tcp
   hepcrawl_scrapyd_1      /docker_entrypoint.sh bash ...   Up


- Attach a running docker container via the following command:

.. code-block:: console

   $ docker exec -it [container_name] /bin/bash

- Monitor the output from all the services (scrapyd, celery worker, ftp server, https server, rabbitmq)
  via the following command:

.. code-block:: console

   $ docker-compose -f docker-compose.test.yml logs -f

