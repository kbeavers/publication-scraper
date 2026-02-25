import pytest

from pubscraper.filters import (
    author_name_matches,
    publication_has_ut_affiliation_for_author,
    filter_publications_for_author,
    filter_all_publications_by_author_and_affiliation,
)


# --- author_name_matches ---


def test_author_name_matches_same_person():
    assert author_name_matches("Beavers Kelsey m", "Kelsey M Beavers") is True
    assert author_name_matches("Beavers Kelsey m", "Kelsey Beavers") is True
    assert author_name_matches("Carson James", "James Carson") is True
    assert author_name_matches("Allen William J", "William J Allen") is True


def test_author_name_matches_different_last_name():
    assert author_name_matches("Beavers Kelsey m", "Smith Kelsey M") is False


def test_author_name_matches_different_first_initial():
    assert author_name_matches("Beavers Kelsey m", "Kelsey R Beavers") is False
    assert author_name_matches("Beavers Kelsey", "Kevin Beavers") is False


def test_author_name_matches_middle_initial():
    assert author_name_matches("Beavers Kelsey m", "Kelsey M Beavers") is True
    assert author_name_matches("Beavers Kelsey m", "Kelsey R Beavers") is False


def test_author_name_matches_comma_form():
    assert author_name_matches("Beavers Kelsey", "Beavers, Kelsey") is True


# --- publication_has_ut_affiliation_for_author ---


def test_has_ut_affiliation_match():
    pub = {
        "affiliations": [
            {
                "author": "Kelsey M Beavers",
                "affiliations": [
                    "The University of Texas at Austin Texas Advanced Computing Center, Austin, TX, USA."
                ],
            }
        ]
    }
    assert publication_has_ut_affiliation_for_author(pub, "Beavers Kelsey m") is True


def test_has_ut_affiliation_ut_arlington():
    pub = {
        "affiliations": [
            {
                "author": "Kelsey M Beavers",
                "affiliations": [
                    "Department of Biology, University of Texas at Arlington, Arlington, TX, USA."
                ],
            }
        ]
    }
    assert publication_has_ut_affiliation_for_author(pub, "Beavers Kelsey") is True


def test_has_ut_affiliation_tacc():
    pub = {
        "affiliations": [
            {
                "author": "Kelsey M Beavers",
                "affiliations": ["Texas Advanced Computing Center, Austin, TX, USA."],
            }
        ]
    }
    assert publication_has_ut_affiliation_for_author(pub, "Beavers Kelsey m") is True


def test_has_ut_affiliation_md_anderson():
    pub = {
        "affiliations": [
            {
                "author": "Jane Doe",
                "affiliations": ["UT MD Anderson Cancer Center, Houston, TX, USA."],
            }
        ]
    }
    assert publication_has_ut_affiliation_for_author(pub, "Doe Jane") is True


def test_no_ut_affiliation():
    pub = {
        "affiliations": [
            {
                "author": "Kelsey R Beavers",
                "affiliations": [
                    "Georgia Institute of Technology, Atlanta, GA, USA."
                ],
            }
        ]
    }
    assert publication_has_ut_affiliation_for_author(pub, "Beavers Kelsey") is False


def test_no_affiliation_data():
    pub = {"affiliations": []}
    assert publication_has_ut_affiliation_for_author(pub, "Beavers Kelsey") is False


def test_author_in_list_but_empty_affiliations():
    pub = {
        "affiliations": [
            {"author": "Kelsey M Beavers", "affiliations": []}
        ]
    }
    assert publication_has_ut_affiliation_for_author(pub, "Beavers Kelsey m") is False


# --- filter_publications_for_author ---


def test_filter_keeps_matching():
    pubs = [
        {
            "title": "UT Paper",
            "affiliations": [
                {
                    "author": "Kelsey M Beavers",
                    "affiliations": ["University of Texas at Arlington, TX"],
                }
            ],
        }
    ]
    filtered = filter_publications_for_author(pubs, "Beavers Kelsey m")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "UT Paper"


def test_filter_removes_non_ut():
    pubs = [
        {
            "title": "Georgia Paper",
            "affiliations": [
                {
                    "author": "Kelsey R Beavers",
                    "affiliations": ["Georgia Institute of Technology, Atlanta, GA"],
                }
            ],
        }
    ]
    filtered = filter_publications_for_author(pubs, "Beavers Kelsey")
    assert len(filtered) == 0


def test_filter_mixed():
    pubs = [
        {
            "title": "UT Paper",
            "affiliations": [
                {
                    "author": "Kelsey M Beavers",
                    "affiliations": ["University of Texas at Austin, TX"],
                }
            ],
        },
        {
            "title": "Other Paper",
            "affiliations": [
                {
                    "author": "Kelsey R Beavers",
                    "affiliations": ["Georgia Institute of Technology"],
                }
            ],
        },
    ]
    filtered = filter_publications_for_author(pubs, "Beavers Kelsey m")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "UT Paper"


# --- filter_all_publications_by_author_and_affiliation ---


def test_filter_all_in_place():
    name_dict = {
        "Beavers Kelsey m": ["Beavers Kelsey m", "The University of Texas at Austin"],
        "Carson James": ["Carson James", "The University of Texas at Austin"],
    }
    authors_and_pubs = [
        {
            "Beavers Kelsey m": [
                {
                    "title": "Keep",
                    "affiliations": [
                        {
                            "author": "Kelsey M Beavers",
                            "affiliations": ["University of Texas at Arlington"],
                        }
                    ],
                },
                {
                    "title": "Drop",
                    "affiliations": [
                        {
                            "author": "Kelsey R Beavers",
                            "affiliations": ["Georgia Institute of Technology"],
                        }
                    ],
                },
            ]
        },
        {
            "Carson James": [
                {
                    "title": "Keep Carson",
                    "affiliations": [
                        {
                            "author": "James Carson",
                            "affiliations": ["UTHealth Houston"],
                        }
                    ],
                }
            ]
        },
    ]
    filter_all_publications_by_author_and_affiliation(authors_and_pubs, name_dict)
    assert len(authors_and_pubs[0]["Beavers Kelsey m"]) == 1
    assert authors_and_pubs[0]["Beavers Kelsey m"][0]["title"] == "Keep"
    assert len(authors_and_pubs[1]["Carson James"]) == 1
    assert authors_and_pubs[1]["Carson James"][0]["title"] == "Keep Carson"
