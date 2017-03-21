# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Contains mappings."""


COMMON_ACRONYMS = [
    'LHC',
    'CFT',
    'QCD',
    'QED',
    'QFT',
    'ABJM',
    'NLO',
    'LO',
    'NNLO',
    'IIB',
    'IIA',
    'MSSM',
    'NMSSM',
    'SYM',
    'WIMP',
    'ATLAS',
    'CMS',
    'ALICE',
    'RHIC',
    'DESY',
    'HERA',
    'CDF',
    'D0',
    'BELLE',
    'BABAR',
    'BFKL',
    'DGLAP',
    'SUSY',
    'QM',
    'UV',
    'IR',
    'BRST',
    'PET',
    'GPS',
    'NMR',
    'XXZ',
    'CMB',
    'LISA',
    'CPT',
    'KEK',
    'TRIUMF',
    'PHENIX',
    'VLBI',
    'NGC',
    'SNR',
    'HESS',
    'AKARI',
    'GALEX',
    'ESO',
    'J-PARC',
    'CERN',
    'XFEL',
    'FAIUR',
    'ILC',
    'CLIC',
    'SPS',
    'BNL',
    'CEBAF',
    'SRF',
    'LINAC',
    'HERMES',
    'ZEUS',
    'H1',
    'GRB'
]

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

MATHML_ELEMENTS = [
    'annotation', 'annotation-xml', 'maction', 'math',
    'merror', 'mfenced', 'mfrac', 'mi', 'mmultiscripts',
    'mn', 'mo', 'mover', 'mpadded',
    'mphantom', 'mprescripts', 'mroot', 'mrow', 'mspace', 'msqrt',
    'mstyle', 'msub', 'msubsup', 'msup', 'mtable', 'mtd', 'mtext',
    'mtr', 'munder', 'munderover', 'none', 'semantics'
]

LANGUAGES = {
    'chi': 'Chinese',
    'cn': 'Chinese',
    'cs': 'Czech',
    'cze': 'Czech',
    'dut': 'Dutch',
    'es': 'Spanish',
    'esp': 'Spanish',
    'fi': 'Finnish',
    'fr': 'French',
    'fre': 'French',
    'ge': 'German',
    'ger': 'German',
    'he': 'Hebrew',
    'heb': 'Hebrew',
    'hu': 'Hungarian',
    'hun': 'Hungarian',
    'id': 'Indonesian',
    'ind': 'Indonesian',
    'it': 'Italian',
    'ita': 'Italian',
    'ja': 'Japanese',
    'jap': 'Japanese',
    'ko': 'Korean',
    'kor': 'Korean',
    'la': 'Latin',
    'lat': 'Latin',
    'nl': 'Dutch',
    'no': 'Norwegian',
    'nor': 'Norwegian',
    'pl': 'Polish',
    'pol': 'Polish',
    'por': 'Portuguese',
    'pt': 'Portuguese',
    'ro': 'Romanian',
    'rom': 'Romanian',
    'ru': 'Russian',
    'rus': 'Russian',
    'sv': 'Swedish',
    'swe': 'Swedish',
}

LICENSES = {  # TODO: more licenses here?
    'creativecommons.org/licenses/by/': 'CC-BY-',
    'creativecommons.org/licenses/by-nc-sa/': 'CC-BY-NC-SA-',
    'arxiv.org/licenses/nonexclusive-distrib/': 'arXiv-'
}

LICENSE_TEXTS = {  # TODO: more licenses here?
    'Creative Commons Attribution-NonCommercial-ShareAlike':
        'https://creativecommons.org/licenses/by-nc-sa/3.0',
    'Creative Commons Attribution 2.0':
        'http://creativecommons.org/licenses/by/2.0/',
    'Creative Commons Attribution 3.0':
        'http://creativecommons.org/licenses/by/3.0/',
    'Creative Commons Attribution 4.0':
        'http://creativecommons.org/licenses/by/4.0/',
}
