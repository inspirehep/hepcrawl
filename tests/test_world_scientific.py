# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, print_function, unicode_literals

import pytest

from hepcrawl.spiders import wcs_spider

from .responses import fake_response_from_file


@pytest.fixture
def results():
    """Return results generator from the WSP spider."""
    spider = wcs_spider.WorldScientificSpider()
    return spider.parse(fake_response_from_file('world_scientific/sample_ws_record.xml'))


def test_abstract(results):
    """Test simple API for extracting and linking files to TeX."""
    abstract = (
        "<p><roman>CH</roman><sub>3</sub><roman>NH</roman><sub>3</sub><roman>PbX</roman>(<roman>X</roman> = <roman>Br</roman>,"
        " <roman>I</roman>, <roman>Cl</roman>) perovskites have recently been used as light absorbers in hybrid organic-inorganic"
        " solid-state solar cells, with efficiencies above 15%. To date, it is essential to add Lithium bis(Trifluoromethanesulfonyl)Imide"
        " (<roman>LiTFSI</roman>) to the hole transport materials (HTM) to get a higher conductivity. However, the detrimental effect of high"
        " <roman>LiTFSI</roman> concentration on the charge transport, DOS in the conduction band of the <roman>TiO</roman><sub>2</sub> substrate"
        " and device stability results in an overall compromise for a satisfactory device. Using a higher mobility hole conductor to avoid lithium"
        " salt is an interesting alternative. Herein, we successfully made an efficient perovskite solar cell by applying a hole conductor PTAA"
        " (Poly[bis(4-phenyl) (2,4,6-trimethylphenyl)-amine]) in the absence of <roman>LiTFSI</roman>. Under AM 1.5 illumination of 100 mW/cm<sup>2</sup>,"
        " an efficiency of 10.9% was achieved, which is comparable to the efficiency of 12.3% with the addition of 1.3 mM <roman>LiTFSI</roman>."
        " An unsealed device without <roman>Li</roman><sup>+</sup> shows interestingly a promising stability.</p>"
    )
    for record in results:
        assert 'abstract' in record
        assert record['abstract'] == abstract
