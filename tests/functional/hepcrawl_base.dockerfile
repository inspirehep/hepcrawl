# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

FROM centos

RUN yum install -y epel-release && \
    yum update -y && \
    yum install -y \
        file \
        gcc \
        git \
        libffi-devel \
        libxml2-devel \
        libxslt-devel \
        libssl-devel \
        make \
        openssl-devel \
        poppler-utils \
        python-pip \
        python-virtualenv && \
    yum clean all

RUN mkdir /code

ADD /docker_entrypoint.sh /docker_entrypoint.sh
ENTRYPOINT ["/docker_entrypoint.sh"]

WORKDIR /code

CMD true
