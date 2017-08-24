# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import absolute_import, division, print_function

import os

import pytest
from scrapy.crawler import Crawler
from scrapy.http import TextResponse
from scrapy.settings import Settings

from hepcrawl import settings
from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import desy_spider
from hepcrawl.testlib.fixtures import fake_response_from_file


def create_spider():
    custom_settings = Settings()
    custom_settings.setmodule(settings)
    crawler = Crawler(
        spidercls=desy_spider.DesySpider,
        settings=custom_settings,
    )
    return desy_spider.DesySpider.from_crawler(
        crawler,
        source_folder='idontexist_but_it_does_not_matter',
    )


def get_records(response_file_name):
    """Return all results generator from the ``Desy`` spider via pipelines."""
    # environmental variables needed for the pipelines payload
    os.environ['SCRAPY_JOB'] = 'scrapy_job'
    os.environ['SCRAPY_FEED_URI'] = 'scrapy_feed_uri'
    os.environ['SCRAPY_LOG_FILE'] = 'scrapy_log_file'

    spider = create_spider()
    records = spider.parse(
        fake_response_from_file(
            file_name=response_file_name,
            response_type=TextResponse
        )
    )

    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    return (
        pipeline.process_item(
            record,
            spider
        ) for record in records
    )


def get_one_record(response_file_name):
    parsed_items = get_records(response_file_name)
    record = parsed_items.next()
    return record


def override_generated_fields(record):
    record['acquisition_source']['datetime'] = '2017-05-04T17:49:07.975168'
    record['acquisition_source']['submission_number'] = (
        '5652c7f6190f11e79e8000224dabeaad'
    )

    return record


@pytest.mark.parametrize(
    'generated_record',
    [
        get_one_record('desy/desy_record.xml'),
    ],
    ids=[
        'smoke',
    ]
)
def test_pipeline_record(generated_record):
    expected = {
        '$schema': 'hep.json',
        '_fft': [
            {
                'creation_datetime': '2017-06-27T09:43:17',
                'description': (
                    '00013 Decomposition of the problematic rotation curves '
                    'in our sample according to the best-fit '
                    '\\textsc{core}NFW models. Colors and symbols are as in '
                    'Figure \\ref{fig:dc14_fits}.'
                ),
                'filename': 'cNFW_rogue_curves',
                'format': '.txt',
                'path': 'FFT/test_fft_1.txt',
                'type': 'Main',
                'version': 1,
            },
            {
                'creation_datetime': '2017-06-27T09:43:16',
                'description': (
                    '00005 Comparison of the parameters of the best-fit DC14 '
                    'models to the cosmological halo mass-concentration '
                    'relation from \\cite{dutton14} (left) and the stellar '
                    'mass-halo mass relation from \\cite{behroozi13} (right). '
                    'The error bars correspond to the extremal values of the '
                    'multidimensional 68\\% confidence region for each fit. '
                    'The theoretical relations are shown as red lines and '
                    'their 1$\\sigma$ and 2$\\sigma$ scatter are represented '
                    'by the dark and light grey bands, respectively. The '
                    'mass-concentration relation from \\cite{maccio08} and '
                    'the stellar mass-halo mass relation from '
                    '\\cite{behroozi13} are also shown as the black dashed '
                    'lines.'
                ),
                'filename': 'scalingRelations_DutBeh_DC14_all_Oh',
                'format': '.txt',
                'path': 'FFT/test_fft_2.txt',
                'type': 'Main',
                'version': 1
            }
        ],
        'abstracts': [
            {
                'source': 'Deutsches Elektronen-Synchrotron',
                'value': (
                    'Dielectric laser acceleration of electrons has recently '
                    'been\n                demonstrated with significantly '
                    'higher accelerating gradients than other\n             '
                    '   structure-based linear accelerators. Towards the '
                    'development of an integrated 1 MeV\n                '
                    'electron accelerator based on dielectric laser '
                    'accelerator technologies,\n                development '
                    'in several relevant technologies is needed. In this '
                    'work, recent\n                developments on electron '
                    'sources, bunching, accelerating, focussing, deflecting '
                    'and\n                laser coupling structures are '
                    'reported. With an eye to the near future, '
                    'components\n                required for a 1 MeV kinetic '
                    'energy tabletop accelerator producing '
                    'sub-femtosecond\n                electron bunches are '
                    'outlined.\n            '
                )
            }
        ],
        'acquisition_source': {
            'datetime': '2017-05-04T17:49:07.975168',
            'method': 'hepcrawl',
            'source': 'desy',
            'submission_number': '5652c7f6190f11e79e8000224dabeaad'
        },
        'control_number': 111111,
        'document_type': [
            'article'
        ],
        'dois': [
            {
                'value': '10.18429/JACoW-IPAC2017-WEYB1'
            }
        ],
        'number_of_pages': 6,
        'public_notes': [
            {
                'value': '*Brief entry*'
            }
        ],
        'publication_info': [
            {
                'parent_isbn': '9783954501823'
            },
            {
                'page_end': '2525',
                'page_start': '2520',
                'year': 2017
            }
        ],
        'self': {
            '$ref': 'https://labs.inspirehep.net/api/literature/111111'
        },
        'titles': [
            {
                'source': 'JACoW',
                'title': (
                    'Towards a Fully Integrated Accelerator on a Chip: '
                    'Dielectric Laser\n                Acceleration (DLA) '
                    'From the Source to Relativistic Electrons\n            '
                )
            }
        ]
    }

    assert override_generated_fields(generated_record) == expected


@pytest.mark.parametrize(
    'generated_records',
    [
        get_records('desy/desy_collection_records.xml'),
    ],
    ids=[
        'smoke',
    ]
)
def test_pipeline_collection_records(generated_records):
    expected = [{
            "acquisition_source": {
                "source": "desy",
                "method": "hepcrawl",
                "submission_number": "5652c7f6190f11e79e8000224dabeaad",
                "datetime": "2017-05-04T17:49:07.975168"
            },
            "_fft": [
                {
                    'creation_datetime': '2017-06-27T09:43:17',
                    'description': (
                        '00013 Decomposition of the problematic rotation '
                        'curves in our sample according to the best-fit '
                        '\\textsc{core}NFW models. Colors and symbols are as '
                        'in Figure \\ref{fig:dc14_fits}.'
                    ),
                    'filename': 'cNFW_rogue_curves',
                    'format': '.txt',
                    'path': 'FFT/test_fft_1.txt',
                    'type': 'Main',
                    'version': 1,
                },
                {
                    'creation_datetime': '2017-06-27T09:43:16',
                    'description': (
                        '00005 Comparison of the parameters of the best-fit '
                        'DC14 models to the cosmological halo '
                        'mass-concentration relation from \\cite{dutton14} '
                        '(left) and the stellar mass-halo mass relation from '
                        '\\cite{behroozi13} (right). The error bars correspond'
                        ' to the extremal values of the multidimensional 68\\%'
                        ' confidence region for each fit. The theoretical '
                        'relations are shown as red lines and their '
                        '1$\\sigma$ and 2$\\sigma$ scatter are represented '
                        'by the dark and light grey bands, respectively. The '
                        'mass-concentration relation from \\cite{maccio08} '
                        'and the stellar mass-halo mass relation from '
                        '\\cite{behroozi13} are also shown as the black '
                        'dashed lines.'
                    ),
                    'filename': 'scalingRelations_DutBeh_DC14_all_Oh',
                    'format': '.txt',
                    'path': 'FFT/test_fft_2.txt',
                    'type': 'Main',
                    'version': 1
                }
            ],
            "control_number": 111111,
            "public_notes": [
                {
                    "value": "*Brief entry*"
                }
            ],
            "self": {
                "$ref": "https://labs.inspirehep.net/api/literature/111111"
            },
            "number_of_pages": 6,
            "titles": [
                {
                    "source": "JACoW",
                    "title": (
                        'Towards a Fully Integrated Accelerator on a Chip: '
                        'Dielectric Laser\n                Acceleration (DLA) '
                        'From the Source to Relativistic Electrons'
                        '\n            '
                    )
                }
            ],
            "dois": [
                {
                    "value": "10.18429/JACoW-IPAC2017-WEYB1"
                }
            ],
            "publication_info": [
                {
                    "parent_isbn": "9783954501823"
                },
                {
                    "page_start": "2520",
                    "page_end": "2525",
                    "year": 2017
                }
            ],
            "$schema": "hep.json",
            "document_type": [
                "article"
            ],
            "abstracts": [
                {
                    "source": "Deutsches Elektronen-Synchrotron",
                    "value": (
                        "Dielectric laser acceleration of electrons has "
                        "recently been\n                demonstrated with "
                        "significantly higher accelerating gradients than "
                        "other\n                structure-based linear "
                        "accelerators. Towards the development of an "
                        "integrated 1 MeV\n                electron "
                        "accelerator based on dielectric laser accelerator "
                        "technologies,\n                development in "
                        "several relevant technologies is needed. In this work"
                        ", recent\n                developments on electron "
                        "sources, bunching, accelerating, focussing, "
                        "deflecting and\n                laser coupling "
                        "structures are reported. With an eye to the near "
                        "future, components\n                required for a 1 "
                        "MeV kinetic energy tabletop accelerator producing sub"
                        "-femtosecond\n                electron bunches are "
                        "outlined.\n            "
                    )
                }
            ]
        },
        {
            "acquisition_source": {
                "source": "desy",
                "method": "hepcrawl",
                "submission_number": "5652c7f6190f11e79e8000224dabeaad",
                "datetime": "2017-05-04T17:49:07.975168"
            },
            "_fft": [
                {
                    'creation_datetime': '2017-06-27T09:43:17',
                    'description': (
                        "00013 Decomposition of the problematic rotation "
                        "curves in our sample according to the best-fit "
                        "\\textsc{core}NFW models. Colors and symbols are as "
                        "in Figure \\ref{fig:dc14_fits}."
                    ),
                    'filename': 'cNFW_rogue_curves',
                    'format': '.txt',
                    'path': 'FFT/test_fft_1.txt',
                    'type': 'Main',
                    'version': 1,
                },
                {
                    'creation_datetime': '2017-06-27T09:43:16',
                    'description': (
                        '00005 Comparison of the parameters of the best-fit '
                        'DC14 models to the cosmological halo '
                        'mass-concentration relation from \\cite{dutton14} '
                        '(left) and the stellar mass-halo mass relation '
                        'from \\cite{behroozi13} (right). The error bars '
                        'correspond to the extremal values of the '
                        'multidimensional 68\\% confidence region for each '
                        'fit. The theoretical relations are shown as red '
                        'lines and their 1$\\sigma$ and 2$\\sigma$ scatter '
                        'are represented by the dark and light grey bands, '
                        'respectively. The mass-concentration relation '
                        'from \\cite{maccio08} and the stellar mass-halo '
                        'mass relation from \\cite{behroozi13} are also '
                        'shown as the black dashed lines.'
                    ),
                    'filename': 'scalingRelations_DutBeh_DC14_all_Oh',
                    'format': '.txt',
                    'path': 'FFT/test_fft_2.txt',
                    'type': 'Main',
                    'version': 1
                }
            ],
            "control_number": 222222,
            "public_notes": [
                {
                    "value": "*Brief entry*"
                }
            ],
            "self": {
                "$ref": "https://labs.inspirehep.net/api/literature/222222"
            },
            "number_of_pages": 6,
            "titles": [
                {
                    "source": "JACoW",
                    "title": (
                        "Towards a Fully Integrated Accelerator on a Chip: "
                        "Dielectric Laser\n                Acceleration "
                        "(DLA) From the Source to Relativistic Electrons"
                        "\n            "
                    )
                }
            ],
            "dois": [
                {
                    "value": "10.18429/JACoW-IPAC2017-WEYB1"
                }
            ],
            "publication_info": [
                {
                    "parent_isbn": "9783954501823"
                },
                {
                    "page_start": "2520",
                    "page_end": "2525",
                    "year": 2017
                }
            ],
            "$schema": "hep.json",
            "document_type": [
                "article"
            ],
            "abstracts": [
                {
                    "source": "Deutsches Elektronen-Synchrotron",
                    "value": (
                        "Dielectric laser acceleration of electrons has "
                        "recently been\n                demonstrated with "
                        "significantly higher accelerating gradients than "
                        "other\n                structure-based linear "
                        "accelerators. Towards the development of an "
                        "integrated 1 MeV\n                electron "
                        "accelerator based on dielectric laser accelerator "
                        "technologies,\n                development in "
                        "several relevant technologies is needed. In this "
                        "work, recent\n                developments on "
                        "electron sources, bunching, accelerating, "
                        "focussing, deflecting and\n                laser "
                        "coupling structures are reported. With an eye to "
                        "the near future, components\n                "
                        "required for a 1 MeV kinetic energy tabletop "
                        "accelerator producing sub-femtosecond"
                        "\n                electron bunches are outlined."
                        "\n            "
                    )
                }
            ]
        }
    ]

    generated_results = [
        override_generated_fields(rec) for rec in generated_records
    ]

    assert generated_results == expected
