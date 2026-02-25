import json
import pytest
import responses

from pubscraper.APIClasses import CrossRef
from pubscraper.filters import filter_publications_for_author
import pubscraper.config as config

BASE_URL = config.CROSSREF_URL


def _crossref_response(items, total_results=None):
    """Build a CrossRef API-style JSON response body."""
    if total_results is None:
        total_results = len(items)
    return json.dumps({"message": {"items": items, "total-results": total_results}})


def _make_item(
    title="Sample Paper",
    authors=None,
    doi="10.1234/sample.doi",
    journal="Test Journal",
    date_time="2024-01-15T00:00:00Z",
    affiliations=None,
):
    """Build a single CrossRef work item with optional per-author affiliations."""
    if authors is None:
        authors = [{"given": "John", "family": "Doe"}]
    if affiliations is not None:
        for i, author in enumerate(authors):
            if i < len(affiliations):
                author["affiliation"] = affiliations[i]
    return {
        "title": [title],
        "author": authors,
        "DOI": doi,
        "container-title": [journal],
        "created": {"date-time": date_time},
    }


@pytest.fixture
def mock_api():
    with responses.RequestsMock() as rsps:
        yield rsps


# --- Basic input validation ---


def test_skip_empty_name(mock_api):
    results = CrossRef.search_multiple_authors([""])
    assert results == {}
    assert len(mock_api.calls) == 0


def test_no_input(mock_api):
    results = CrossRef.search_multiple_authors([])
    assert results == {}
    assert len(mock_api.calls) == 0


def test_should_fail():
    cr = CrossRef.CrossRef()
    with pytest.raises(ValueError):
        cr.get_publications_by_author("j l hendrix", -1)


def test_empty_author_returns_none():
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("")
    assert result is None


# --- Extraction helpers ---


def test_extract_authors():
    cr = CrossRef.CrossRef()
    item = {
        "author": [
            {"given": "John", "family": "Doe"},
            {"given": "Jane", "family": "Smith"},
        ]
    }
    assert cr._extract_authors(item) == "John Doe,Jane Smith"


def test_extract_authors_missing_given():
    cr = CrossRef.CrossRef()
    item = {"author": [{"family": "Consortium"}]}
    assert cr._extract_authors(item) == "Consortium"


def test_extract_title():
    cr = CrossRef.CrossRef()
    assert cr._extract_title({"title": ["My Paper"]}) == "My Paper"
    assert cr._extract_title({}) is None


def test_extract_journal():
    cr = CrossRef.CrossRef()
    assert cr._extract_journal({"container-title": ["Nature"]}) == "Nature"
    assert cr._extract_journal({}) is None


def test_extract_publication_date():
    cr = CrossRef.CrossRef()
    item = {"created": {"date-time": "2024-01-15T00:00:00Z"}}
    assert cr._extract_publication_date(item) == "2024-01-15T00:00:00Z"
    assert cr._extract_publication_date({}) is None


def test_extract_affiliations():
    cr = CrossRef.CrossRef()
    item = {
        "author": [
            {
                "given": "John",
                "family": "Doe",
                "affiliation": [{"name": "University of Texas at Austin"}],
            }
        ]
    }
    affs = cr._extract_affiliations(item)
    assert len(affs) == 1
    assert affs[0]["author"] == "John Doe"
    assert "University of Texas at Austin" in affs[0]["affiliations"]


def test_extract_affiliations_empty():
    cr = CrossRef.CrossRef()
    item = {"author": [{"given": "John", "family": "Doe"}]}
    affs = cr._extract_affiliations(item)
    assert len(affs) == 1
    assert affs[0]["author"] == "John Doe"
    assert affs[0]["affiliations"] == []


def test_is_valid_pub():
    cr = CrossRef.CrossRef()
    valid = {"from": "CrossRef", "journal": "J", "title": "T", "doi": "D"}
    assert cr._is_valid_pub(valid)
    invalid = {"from": "CrossRef", "journal": None, "title": "T"}
    assert not cr._is_valid_pub(invalid)


# --- Integration: API returns candidates; post-process filter applies UT + author match ---


def test_keeps_ut_affiliated_publications(mock_api):
    item = _make_item(
        title="UT Paper",
        authors=[{"given": "Kelsey", "family": "Beavers"}],
        affiliations=[[{"name": "University of Texas at Arlington, TX"}]],
    )
    mock_api.add(
        responses.GET,
        BASE_URL,
        body=_crossref_response([item], total_results=1),
        status=200,
    )
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("Beavers Kelsey", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Beavers Kelsey")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "UT Paper"


def test_filters_non_ut_publications(mock_api):
    item = _make_item(
        title="Georgia Tech Paper",
        authors=[{"given": "Kelsey R.", "family": "Beavers"}],
        affiliations=[[{"name": "Georgia Institute of Technology, Atlanta, GA"}]],
    )
    mock_api.add(
        responses.GET,
        BASE_URL,
        body=_crossref_response([item], total_results=1),
        status=200,
    )
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("Beavers Kelsey", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Beavers Kelsey")
    assert len(filtered) == 0


def test_skips_publications_without_affiliations(mock_api):
    """After post-process filter, publications with no UT affiliation are dropped."""
    item = _make_item(
        title="No Affiliation Paper",
        authors=[{"given": "Kelsey", "family": "Beavers"}],
    )
    mock_api.add(
        responses.GET,
        BASE_URL,
        body=_crossref_response([item], total_results=1),
        status=200,
    )
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("Beavers Kelsey", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Beavers Kelsey")
    assert len(filtered) == 0


def test_mixed_results_only_keeps_ut(mock_api):
    """After post-process filter, only UT-affiliated publication is kept."""
    item_ut = _make_item(
        title="UT Paper",
        doi="10.1234/ut",
        authors=[{"given": "Kelsey M", "family": "Beavers"}],
        affiliations=[[{"name": "University of Texas at Austin, TX"}]],
    )
    item_gatech = _make_item(
        title="Georgia Tech Paper",
        doi="10.1234/gatech",
        authors=[{"given": "Kelsey R.", "family": "Beavers"}],
        affiliations=[[{"name": "Georgia Institute of Technology, Atlanta, GA"}]],
    )
    item_no_aff = _make_item(
        title="Mystery Paper",
        doi="10.1234/mystery",
        authors=[{"given": "Kelsey", "family": "Beavers"}],
    )
    mock_api.add(
        responses.GET,
        BASE_URL,
        body=_crossref_response(
            [item_ut, item_gatech, item_no_aff], total_results=3
        ),
        status=200,
    )
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("Beavers Kelsey", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Beavers Kelsey")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "UT Paper"


def test_HTTP_failure(mock_api):
    mock_api.add(responses.GET, BASE_URL, status=500)
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("j l hendrix")
    assert result is None


# --- Output format ---


def test_publication_output_format(mock_api):
    item = _make_item(
        authors=[{"given": "John", "family": "Doe"}],
        affiliations=[[{"name": "University of Texas at Dallas"}]],
    )
    mock_api.add(
        responses.GET,
        BASE_URL,
        body=_crossref_response([item]),
        status=200,
    )
    cr = CrossRef.CrossRef()
    result = cr.get_publications_by_author("Doe John", rows=10)
    assert result is not None
    pub = result[0]
    assert pub["from"] == "CrossRef"
    assert "journal" in pub
    assert "publication_date" in pub
    assert "title" in pub
    assert "authors" in pub
    assert "affiliations" in pub
    assert "doi" in pub
