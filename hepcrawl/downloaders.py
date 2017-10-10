# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Additional downloaders."""


from scrapy.http import Response


class DummyDownloadHandler(object):
    def __init__(self, *args, **kwargs):
        pass

    def download_request(self, request, spider):
        url = request.url
        return Response(url, request=request)
