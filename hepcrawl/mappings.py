# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Contains mappings."""

from __future__ import absolute_import, division, print_function

CONFERENCE_WORDS = [
    'colloquium',
    'colloquiums',
    'conf',
    'conference',
    'conferences',
    'contrib',
    'contributed',
    'contribution',
    'contributions',
    'forum',
    'lecture',
    'lectures',
    'meeting',
    'meetings',
    'pres',
    'presented',
    'proc',
    'proceeding',
    'proceedings',
    'rencontre',
    'rencontres',
    'school',
    'schools',
    'seminar',
    'seminars',
    'symp',
    'symposium',
    'symposiums',
    'talk',
    'talks',
    'workshop',
    'workshops'
]

THESIS_WORDS = [
    'diploma',
    'diplomarbeit',
    'diplome',
    'dissertation',
    'doctoraal',
    'doctoral',
    'doctorat',
    'doctorate',
    'doktorarbeit',
    'dottorato',
    'habilitationsschrift',
    'hochschule',
    'inauguraldissertation',
    'memoire',
    'phd',
    'proefschrift',
    'schlussbericht',
    'staatsexamensarbeit',
    'tesi',
    'thesis',
    'travail'
]

MATHML_ELEMENTS = set([
    'annotation', 'annotation-xml', 'maction', 'math',
    'merror', 'mfenced', 'mfrac', 'mi', 'mmultiscripts',
    'mn', 'mo', 'mover', 'mpadded',
    'mphantom', 'mprescripts', 'mroot', 'mrow', 'mspace', 'msqrt',
    'mstyle', 'msub', 'msubsup', 'msup', 'mtable', 'mtd', 'mtext',
    'mtr', 'munder', 'munderover', 'none', 'semantics'
])

LANGUAGES = {
    'fr': 'French',
    'ru': 'Russian',
    'ge': 'German',
    'es': 'Spanish',
    'la': 'Latin',
    'it': 'Italian',
    'ja': 'Japanese',
    'pt': 'Portuguese',
    'cn': 'Chinese',
    'ro': 'Romanian',
    'pl': 'Polish',
    'nl': 'Dutch',
    'cs': 'Czech',
    'id': 'Indonesian',
    'no': 'Norwegian',
    'sv': 'Swedish',
    'he': 'Hebrew',
    'hu': 'Hungarian',
    'ko': 'Korean',
    'fre': 'French',
    'rus': 'Russian',
    'ger': 'German',
    'esp': 'Spanish',
    'lat': 'Latin',
    'ita': 'Italian',
    'jap': 'Japanese',
    'por': 'Portuguese',
    'chi': 'Chinese',
    'rom': 'Romanian',
    'pol': 'Polish',
    'dut': 'Dutch',
    'cze': 'Czech',
    'ind': 'Indonesian',
    'nor': 'Norwegian',
    'swe': 'Swedish',
    'heb': 'Hebrew',
    'hun': 'Hungarian',
    'kor': 'Korean'
}
