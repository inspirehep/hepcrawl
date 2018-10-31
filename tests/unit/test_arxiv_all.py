# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import pytest

from scrapy.crawler import Crawler
from scrapy.http import TextResponse

from hepcrawl.pipelines import InspireCeleryPushPipeline
from hepcrawl.spiders import arxiv_spider
from hepcrawl.testlib.fixtures import (
    fake_response_from_file,
    clean_dir,
)


@pytest.fixture
def spider():
    crawler = Crawler(spidercls=arxiv_spider.ArxivSpider)
    spider = arxiv_spider.ArxivSpider.from_crawler(crawler)
    return spider


@pytest.fixture
def many_results(spider):
    """Return results generator from the arxiv spider. Tricky fields, many
    records.
    """
    def _get_processed_record(item, spider):
        crawl_result = pipeline.process_item(item, spider)
        return crawl_result['record']

    fake_response = fake_response_from_file(
        'arxiv/sample_arxiv_record.xml',
        response_type=TextResponse,
    )

    test_selectors = fake_response.xpath('.//record')
    parsed_items = [spider.parse_record(sel) for sel in test_selectors]
    pipeline = InspireCeleryPushPipeline()
    pipeline.open_spider(spider)

    yield [
        _get_processed_record(parsed_item, spider)
        for parsed_item in parsed_items
    ]

    clean_dir()


def test_page_nr(many_results):
    """Test extracting page_nr"""
    page_nrs = [
        6,
        8,
        10,
        11,
        None,
        4,
        8,
        24,
        23,
        None,
        None,
        43,
    ]
    for page_nr, record in zip(page_nrs, many_results):
        assert record.get('number_of_pages') == page_nr


def test_collections(many_results):
    """Test journal type"""
    doctypes = [
        ['conference paper'],
        ['conference paper'],
        ['conference paper'],
        ['conference paper'],
        ['article'],
        ['conference paper'],
        ['article'],
        ['article'],
        ['article'],
        ['conference paper'],
        ['thesis'],
        ['article'],
    ]

    for doctypes, record in zip(doctypes, many_results):
        assert record.get('citeable')
        assert record.get('document_type') == doctypes


def test_collaborations(many_results):
    """Test extracting collaboration."""
    collaborations = [
        ["Planck", ],
        ["IceCube", ],
        ["JLQCD", ],
        ["NuPRISM", "Hyper-K"],
        ['BICEP2', 'Keck Array'],
        ["Planck", ],
        ["DES", ],
        [],
        ['Super-Kamiokande'],
        ['CMS'],
        [],
        ['ATLAS'],
    ]
    for num, record in enumerate(many_results):
        collaboration = collaborations[num]
        if collaboration:
            record_collaboration = [
                coll['value'] for coll in record['collaborations']
            ]
            assert 'collaborations' in record
            assert record_collaboration == collaboration
        else:
            assert 'collaborations' not in record


def test_authors(many_results):
    """Test authors."""
    full_names = [
        ['Wang, Jieci', 'Tian, Zehua', 'Jing, Jiliang', 'Fan, Heng'],
        ['Montaruli, Teresa Maria', ],
        ['Sinya', ],
        ['Scott, Mark', ],
        ['Ade, P.', 'Ahmed, Z.', 'Aikin, R.W.', 'Alexander, K.D.'],
        [
            'Burigana, Günter',
            'Trombetti, Tiziana',
            'Paoletti, Daniela',
            'Mandolesi, Nazzareno',
            'Natoli, Paolo',
        ],
        ['Bufanda, E.', 'Hollowood, D.'],
        ['Saxton Walton, Curtis J.', 'Younsi, Ziri', 'Wu, Kinwah'],
        [
            'Abe, K.',
            'Suzuki, Y.',
            'Vagins, M.R.',
            'Nantais, C.M.',
            'Martin, J.F.',
            'de Perio, P.',
        ],
        ['Chudasama, Ruchi', 'Dutta, Dipanwita'],
        ['Battista, Emmanuele', ],
        ['Aaboud, Morad'],
    ]
    affiliations = [
        [[], [], [], []],
        [[], ],
        [[], ],
        [[], ],
        [[], [], [], []],
        [[], [], [], [], []],
        [[], []],
        [['Technion', 'DESY'], ['U.Frankfurt'], []],
        [
            [
                (
                    'Kamioka Observatory, Institute for Cosmic Ray Research, '
                    'University of Tokyo'
                ),
                (
                    'Kavli Institute for the Physics and Mathematics of the '
                    'Universe'
                ),
            ],
            ['Kavli Institute for the Physics and Mathematics of the Universe'],
            [
                (
                    'Kavli Institute for the Physics and Mathematics of the '
                    'Universe'
                ),
                (
                    'Department of Physics and Astronomy, University of '
                    'California, Irvine'
                ),
            ],
            ['Department of Physics, University of Toronto'],
            ['Department of Physics, University of Toronto'],
            ['Department of Physics, University of Toronto']
        ],
        [[], []],
        [[], ],
        [[]],
    ]
    for num, record in enumerate(many_results):
        test_full_names = full_names[num]
        test_affiliations = affiliations[num]
        assert 'authors' in record
        assert len(record['authors']) == len(test_full_names)
        record_full_names = [
            author['full_name'] for author in record['authors']
        ]
        record_affiliations = []
        for author in record['authors']:
            record_affiliations.append(
                [aff['value'] for aff in author.get('raw_affiliations', [])]
            )
        # assert that we have the same list of authors
        assert set(test_full_names) == set(record_full_names)
        # assert that we have the same list of affiliations
        assert test_affiliations == record_affiliations


def test_repno(many_results):
    """Test extracting repor numbers."""
    expected_repnos = [
        None,
        None,
        [{
            'value': 'YITP-2016-26',
            'source': 'arXiv',
        }],
        None,
        None,
        None,
        [
            {'source': 'arXiv', 'value': u'DES 2016-0158'},
            {'source': 'arXiv', 'value': u'FERMILAB PUB-16-231-AE'}
        ],
        None,
        None,
        None,
        None,
        [{
            'value': u'CERN-EP-2018-143',
            'source': 'arXiv',
        }]
    ]
    for index, (expected_repno, record) in enumerate(
        zip(expected_repnos, many_results)
    ):
        if expected_repno:
            assert 'report_numbers' in record
            assert record['report_numbers'] == expected_repno
        else:
            assert 'report_numbers' not in record


def test_abstracts(many_results):
    """Test extracting abstracts"""
    abstracts = [
        [{
            'source': 'arXiv',
            'value': "We study the dynamics of quantum coherence under Unruh thermal noise and seek under which " +
            "condition the coherence can be frozen in a relativistic setting. We find that the quantum " +
            "coherence can not be frozen for any acceleration due to the effect of Unruh thermal noise. " +
            "We also find that quantum coherence is more robust than entanglement under the effect of " +
            "Unruh thermal noise and therefore the coherence type quantum resources are more accessible " +
            "for relativistic quantum information processing tasks. Besides, the dynamic of quantum coherence " +
            "is found to be more sensitive than entanglement to the preparation of the detectors' initial " +
            "state and the atom-field coupling strength, while it is less sensitive than entanglement to the " +
            "acceleration of the detector.",
        }],
        [{
            'source': 'arXiv',
            'value': "In this contribution we summarize the selected highlights of IceCube in thedomain of high-energy " +
            "astrophysics and particle physics. We discuss thehighest-energy neutrino detection and its " +
            "interpretation after 4 years of data.The significance is such that the discovery of a non " +
            "terrestrial component canbe claimed but its origin is not yet clarified. The high energy " +
            "non-atmosphericcomponent is seen also in other analyses with smaller significance, forinstance " +
            "when using muon neutrino induced events coming from the Northernhemisphere. Flavor mixing " +
            "is probed along cosmic distances in an analysis usingalso cascade neutrino events. The results " +
            "on the search for neutrino sources ispresented including the results of a joint analysis with " +
            "Pierre Auger andTelescope Array which is sensitive to correlations between highest energyneutrinos " +
            "and UHECRs measured by the three experiments. Moreover, recentresults on dark matter searches " +
            "from the Sun are discussed. Finally, theresults on standard neutrino oscillations are presented.",
        }],
        [{
            'source': 'arXiv',
            'value': "We discuss the fate of the axial U(1) symmetry in 2-flavor QCD at finitetemperature, where " +
            "the non-singlet chiral symmetry is restored. We firstsummarize the previous theoretical " +
            "investigation on the relation between theeigenvalue density of the Dirac operator and the " +
            "axial U(1) symmetry. We showthat the eigenvalue density near the origin behaves as $\lambda^\gamma$ " +
            "with$\gamma > 2$ in the chirally symmetric phase, where $\lambda$ is an eigenvalue.This " +
            "implies that the axial U(1) symmetry is partially restored, so that thelow energy symmetry " +
            "of the theory becomes SU(2)$\otimes$ SU(2)$\otimes$ Z$_4$.Secondly, we report recent numerical " +
            "investigations on this issue by latticeQCD simulations with lattice chiral fermions such as " +
            "Overlap or improveddomain-wall fermions. Our preliminary results indicate that the eigenvaluedensity " +
            "seems to have a gap at the origin just above $T_c$, the temperature ofthe chiral symmetry " +
            "restoration, which implies the axial U(1) symmetry iseffectively restored at high temperature. " +
            "We also point out an importance ofthe exact lattice chiral symmetry to obtain correct results " +
            "on this issue.",
        }],
        [{
            'source': 'arXiv',
            'value': "Recent neutrino oscillation results have shown that the existing longbaseline experiments " +
            "have some sensitivity to the effects of CP violation inthe neutrino sector. This sensitivity " +
            "is currently statistically limited, butthe next generation of experiments, DUNE and Hyper-K, " +
            "will provide an order ofmagnitude more events. To reach the full potential of these datasets " +
            "we mustachieve a commensurate improvement in our understanding of the systematicuncertainties " +
            "that beset them. This talk describes two proposed intermediatedetectors for the current and " +
            "future long baseline oscillation experiments inJapan, TITUS and NuPRISM. These detectors are " +
            "discussed in the context of thecurrent T2K oscillation analysis, highlighting the ways in which " +
            "they couldreduce the systematic uncertainty on this measurement. The talk also describesthe " +
            "short baseline oscillation sensitivity of NuPRISM along with the neutrinoscattering measurements " +
            "the detector makes possible.",
        }],
        [{
            'source': 'arXiv',
            'value': "A linear polarization field on the sphere can be uniquely decomposed into anE-mode and a B-mode " +
            "component. These two components are analytically defined interms of spin-2 spherical harmonics. " +
            "Maps that contain filtered modes on apartial sky can also be decomposed into E-mode and B-mode " +
            "components. However,the lack of full sky information prevents orthogonally separating thesecomponents " +
            "using spherical harmonics. In this paper, we present a technique fordecomposing an incomplete " +
            "map into E and B-mode components using E and Beigenmodes of the pixel covariance in the observed " +
            "map. This method is found toorthogonally define E and B in the presence of both partial sky " +
            "coverage andspatial filtering. This method has been applied to the BICEP2 and the KeckArray " +
            "maps and results in reducing E to B leakage from LCDM E-modes to a levelcorresponding to a " +
            "tensor-to-scalar ratio of $r<1\\times10^{-4}$.",
        }],
        [{
            'source': 'arXiv',
            'value': "The Planck Collaboration has recently released maps of the microwave sky inboth temperature " +
            "and polarization. Diffuse astrophysical components (includingGalactic emissions, cosmic far " +
            "infrared (IR) background, y-maps of the thermalSunyaev-Zeldovich (SZ) effect) and catalogs " +
            "of many thousands of Galactic andextragalactic radio and far-IR sources, and galaxy clusters " +
            "detected throughthe SZ effect are the main astrophysical products of the mission. A conciseoverview " +
            "of these results and of astrophysical studies based on Planck data ispresented.",
        }],
        [{
            'source': 'arXiv',
            'value': "The correlation between active galactic nuclei (AGN) and environment providesimportant clues " +
            "to AGN fueling and the relationship of black hole growth togalaxy evolution. In this paper, " +
            "we analyze the fraction of galaxies inclusters hosting AGN as a function of redshift and cluster " +
            "richness for X-raydetected AGN associated with clusters of galaxies in Dark Energy Survey " +
            "(DES)Science Verification data. The present sample includes 33 AGN with L_X > 10^43ergs s^-1 " +
            "in non-central, host galaxies with luminosity greater than 0.5 L*from a total sample of 432 " +
            "clusters in the redshift range of 0.1<z<0.95.Analysis of the present sample reveals that the AGN " +
            "fraction in red-sequencecluster members has a strong positive correlation with redshift such that " +
            "theAGN fraction increases by a factor of ~ 8 from low to high redshift, and thefraction of cluster " +
            "galaxies hosting AGN at high redshifts is greater than thelow-redshift fraction at 3.6 sigma. In " +
            "particular, the AGN fraction increasessteeply at the highest redshifts in our sample at z>0.7. " +
            "This result is in goodagreement with previous work and parallels the increase " +
            "in star formation incluster galaxies over the same redshift range. However, the AGN fraction " +
            "inclusters is observed to have no significant correlation with cluster mass.Future analyses " +
            "with DES Year 1 and 2 data will be able to clarify whether AGNactivity is correlated to " +
            "cluster mass and will tightly constrain therelationship between cluster AGN populations and " +
            "redshift.",
        }],
        [{
            'source': 'arXiv',
            'value': "We calculate the radial profiles of galaxies where the nuclear region isself-gravitating, " +
            "consisting of self-interacting dark matter (SIDM) with $F$degrees of freedom. For sufficiently " +
            "high density this dark matter becomescollisional, regardless of its behaviour on galaxy " +
            "scales. Our calculationsshow a spike in the central density profile, with properties determined " +
            "by thedark matter microphysics, and the densities can reach the `mean density' of ablack hole " +
            "(from dividing the black-hole mass by the volume enclosed by theSchwarzschild radius). For a " +
            "galaxy halo of given compactness($\chi=2GM/Rc^2$), certain values for the dark matter entropy " +
            "yield a densecentral object lacking an event horizon. For some soft equations of state ofthe " +
            "SIDM (e.g. $F\ge6$), there are multiple horizonless solutions at givencompactness. Although " +
            "light propagates around and through a sphere composed ofdark matter, it is gravitationally " +
            "lensed and redshifted. While somecalculations give non-singular solutions, others yield solutions " +
            "with a centralsingularity. In all cases the density transitions smoothly from the centralbody " +
            "to the dark-matter envelope around it, and to the galaxy's dark matterhalo. We propose that " +
            "pulsar timing observations will be able to distinguishbetween systems with a centrally dense " +
            "dark matter sphere (for differentequations of state) and conventional galactic nuclei that " +
            "harbour asupermassive black hole.",
        }],
        [{
            'source': 'arXiv',
            'value': "Upgraded electronics, improved water system dynamics, better calibration andanalysis " +
            "techniques allowed Super-Kamiokande-IV to clearly observe verylow-energy 8B solar neutrino " +
            "interactions, with recoil electron kineticenergies as low as 3.49 MeV. Super-Kamiokande-IV " +
            "data-taking began in Septemberof 2008; this paper includes data until February 2014, a " +
            "total livetime of 1664days. The measured solar neutrino flux is (2.308+-0.020(stat.) " +
            "+0.039-0.040(syst.)) x 106/(cm2sec) assuming no oscillations. The observedrecoil electron " +
            "energy spectrum is consistent with no distortions due toneutrino oscillations. An extended " +
            "maximum likelihood fit to the amplitude ofthe expected solar zenith angle variation of the " +
            "neutrino-electron elasticscattering rate in SK-IV results in a day/night asymmetry " +
            "of(-3.6+-1.6(stat.)+-0.6(syst.))%. The SK-IV solar neutrino data determine thesolar mixing " +
            "angle as sin2 theta_12 = 0.327+0.026-0.031, all SK solar data(SK-I, SK-II, SK III and SKIV) " +
            "measures this angle to be sin2 theta_12 =0.334+0.027-0.023, the determined mass-squared " +
            "splitting is Delta m2_21 =4.8+1.5-0.8 x10-5 eV2.",
        }],
        [{
            'source': 'arXiv',
            'value': "Results of exclusive photoproduction of Upsilon states in Ultraperipheralcollisions (UPC) " +
            "of protons and ions with the CMS experiment are presented,which provides a clean probe of " +
            "the gluon distribution at small values ofparton fractional momenta $x \\approx 10^{-2} 10^{4}$ " +
            "at central rapidities (|y|$< 2.5$). The three Upsilon states (1S, 2S, 3S) are measured in " +
            "the dimuondecay channel along with the photon-photon decaying to dimuon QED continuum " +
            "at$\sqrt{s_{NN}}=5.02$~TeV for integrated luminosity of $L_{int} = 35$ nb$^{-1}$.The total " +
            "Upsilon photoproduction cross sections at different photon-protoncenter of mass energy " +
            "$W_{\gamma p}$ and t-differential distributions arepresented and compared with other " +
            "experimental results as well as theoreticalpredictions.",
        }],
        [{
            'source': 'arXiv',
            'value': 'The thesis is divided into two parts. In the first part the low-energy limitof quantum ' +
            'gravity is analysed, whereas in the second we deal with thehigh-energy domain. In the ' +
            'first part, by applying the effective field theorypoint of view to the quantization of ' +
            'general relativity, detectable, thoughtiny, quantum effects in the position of Newtonian ' +
            'Lagrangian points of theEarth-Moon system are found. In order to make more realistic the ' +
            'quantumcorrected model proposed, the full three-body problem where the Earth and theMoon ' +
            'interact with a generic massive body and the restricted four-body probleminvolving the ' +
            'perturbative effects produced by the gravitational presence ofthe Sun in the Earth-Moon ' +
            'system are also studied. After that, a new quantumtheory having general relativity as its ' +
            'classical counterpart is analysed. Byexploiting this framework, an innovative interesting ' +
            'prediction involving theposition of Lagrangian points within the context of general relativity ' +
            'isdescribed. Furthermore, the new pattern provides quantum corrections to therelativistic ' +
            'coordinates of Earth-Moon libration points of the order of fewmillimetres. The second part ' +
            'of the thesis deals with the Riemannian curvaturecharacterizing the boosted form assumed by ' +
            'the Schwarzschild-de Sitter metric.The analysis of the Kretschmann invariant and the geodesic ' +
            'equation shows thatthe spacetime possesses a "scalar curvature singularity" within a 3-sphere ' +
            'andthat it is possible to define what we here call "boosted horizon", a sort ofelastic wall ' + 
            'where all particles are surprisingly pushed away, suggesting thatsuch "boosted geometries" ' +
            'are ruled by a sort of "antigravity effect".Eventually, the equivalence with the coordinate ' +
            'shift method is invoked inorder to demonstrate that all $\delta^2$ terms appearing in the ' +
            'Riemanncurvature tensor give vanishing contribution in distributional sense.',
        }],
        [{
            'source': 'arXiv',
            'value': "Results of a search for the pair production of photon-jets---collimated groupings of " +
            "photons---in the ATLAS detector at the Large Hadron Collider are reported. Highly collimated " +
            "photon-jets can arise from the decay of new, highly boosted particles that can decay to " +
            "multiple photons collimated enough to be identified in the electromagnetic calorimeter as " +
            "a single, photon-like energy cluster. Data from proton--proton collisions at a center-of-mass " +
            "energy of 13 TeV, corresponding to an integrated luminosity of 36.7 fb$^{-1}$, were collected " +
            "in 2015 and 2016. Candidate photon-jet pair production events are selected from those containing " +
            "two reconstructed photons using a set of identification criteria much less stringent than " +
            "that typically used for the selection of photons, with additional criteria applied to provide " +
            "improved sensitivity to photon-jets. Narrow excesses in the reconstructed diphoton mass " +
            "spectra are searched for. The observed mass spectra are consistent with the Standard Model " +
            "background expectation. The results are interpreted in the context of a model containing a " +
            "new, high-mass scalar particle with narrow width, $X$, that decays into pairs of photon-jets " +
            "via new, light particles, $a$. Upper limits are placed on the cross-section times the product " +
            "of branching ratios $\sigma \\times \mathcal{B}(X \\rightarrow aa) \\times \mathcal {B}(a " +
            "\\rightarrow \gamma \gamma)^{2}$ for 200 GeV $< m_{X} <$ 2 TeV and for ranges of $ m_a $ " +
            "from a lower mass of 100 MeV up to between 2 GeV and 10 GeV, depending upon $ m_X $. Upper " +
            "limits are also placed on $\sigma \\times \mathcal{B}(X \\rightarrow aa) \\times \mathcal " +
            "{B}(a \\rightarrow 3\pi^{0})^{2}$ for the same range of $ m_X $ and for ranges of $ m_a $ " +
            "from a lower mass of 500 MeV up to between 2 GeV and 10 GeV.",
        }],
    ]
    for abstract, record in zip(abstracts, many_results):
        assert record.get('abstracts') == abstract
