import pytest
import responses

from pubscraper.APIClasses import PubMed
from pubscraper.filters import filter_publications_for_author

SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

SAMPLE_XML_UT = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Journal>
          <Title>some journal</Title>
          <JournalIssue><PubDate><Year>2000</Year><Month>Sep</Month><Day>06</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>BiasNet</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Allen</LastName>
            <ForeName>William J</ForeName>
            <AffiliationInfo>
              <Affiliation>University of Texas at Austin, TX, USA.</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/test</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

SAMPLE_XML_TWO_ARTICLES = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Journal>
          <Title>some journal</Title>
          <JournalIssue><PubDate><Year>2000</Year><Month>Sep</Month><Day>06</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>BiasNet</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Allen</LastName>
            <ForeName>William J</ForeName>
            <AffiliationInfo>
              <Affiliation>Texas Advanced Computing Center, Austin, TX, USA.</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/test1</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Journal>
          <Title>another journal</Title>
          <JournalIssue><PubDate><Year>2001</Year><Month>Jan</Month><Day>15</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>Another Paper</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Allen</LastName>
            <ForeName>William J</ForeName>
            <AffiliationInfo>
              <Affiliation>University of Texas at Arlington, Arlington, TX, USA.</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/test2</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

SAMPLE_XML_NON_UT = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Journal>
          <Title>some journal</Title>
          <JournalIssue><PubDate><Year>2020</Year><Month>Jan</Month><Day>01</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>Some Paper</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
            <AffiliationInfo>
              <Affiliation>Georgia Institute of Technology, Atlanta, GA, USA.</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/test3</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

SAMPLE_XML_MIXED = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Journal>
          <Title>journal one</Title>
          <JournalIssue><PubDate><Year>2023</Year><Month>May</Month><Day>22</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>UT Paper</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Beavers</LastName>
            <ForeName>Kelsey M</ForeName>
            <AffiliationInfo>
              <Affiliation>University of Texas at Arlington, Arlington, TX, USA.</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/ut</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <Article>
        <Journal>
          <Title>journal two</Title>
          <JournalIssue><PubDate><Year>2012</Year><Month>Dec</Month><Day>22</Day></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>Georgia Tech Paper</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Beavers</LastName>
            <ForeName>Kelsey R</ForeName>
            <AffiliationInfo>
              <Affiliation>Georgia Institute of Technology, Atlanta, GA, USA.</Affiliation>
            </AffiliationInfo>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/gatech</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""


def _mock_search(rsps, url=SEARCH_URL, id_list=None, status=200):
    """Helper to add a search response mock."""
    if id_list is None:
        id_list = ["12345678"]
    rsps.add(
        responses.GET,
        url,
        json={"esearchresult": {"idlist": id_list}},
        status=status,
    )


def _mock_fetch(rsps, xml=SAMPLE_XML_UT, url=FETCH_URL, status=200):
    """Helper to add a fetch response mock."""
    rsps.add(
        responses.GET,
        url,
        body=xml,
        status=status,
        content_type="text/xml",
    )


# --- Basic input validation ---


def test_skip_empty_name():
    results = PubMed.search_multiple_authors([""])
    assert results == {}


def test_no_input():
    results = PubMed.search_multiple_authors([])
    assert results == {}


def test_bad_author_name():
    pb = PubMed.PubMed()
    result = pb._get_UIDs_by_author("")
    assert result is None


def test_failure_multiple_authors():
    empty_results = PubMed.search_multiple_authors(["kelsey", "erik"], -1)
    assert empty_results == {}


# --- Name parsing ---


def test_parse_author_name():
    pb = PubMed.PubMed()
    assert pb._parse_author_name("Beavers Kelsey m") == ("Beavers", "Kelsey", "m")
    assert pb._parse_author_name("Carson James") == ("Carson", "James", "")
    assert pb._parse_author_name("Smith John Michael") == ("Smith", "John", "Michael")


# --- Search and fetch ---


@responses.activate
def test_partial_empty_input():
    _mock_search(responses)
    _mock_fetch(responses)
    results = PubMed.search_multiple_authors(["Allen William"])
    assert len(results) == 1


@responses.activate
def test_search_all_names():
    for _ in range(3):
        _mock_search(responses)
        _mock_fetch(responses)

    results = PubMed.search_multiple_authors(
        ["Allen William", "Allen William", "Allen William"]
    )
    assert len(results) >= 1


@responses.activate
def test_no_results():
    _mock_search(responses, id_list=[])
    _mock_search(responses, id_list=[])
    results = PubMed.search_multiple_authors(["Hendrix Joseph L"])
    assert results == {}


@responses.activate
def test_initials_lastname():
    _mock_search(responses)
    _mock_fetch(responses)

    results = PubMed.search_multiple_authors(["Allen W J"])
    publications_found = results.get("Allen W J", [])
    biasnet_found = any("BiasNet" in pub["title"] for pub in publications_found)
    assert biasnet_found


@responses.activate
def test_fullname():
    _mock_search(responses)
    _mock_fetch(responses, xml=SAMPLE_XML_TWO_ARTICLES)

    results = PubMed.search_multiple_authors(["Allen William Joseph"])
    publications_found = results.get("Allen William Joseph", [])
    biasnet_found = any("BiasNet" in pub["title"] for pub in publications_found)
    assert biasnet_found


@responses.activate
def test_limit_number_of_results():
    _mock_search(responses, id_list=["12345678", "23456789"])
    _mock_fetch(responses, xml=SAMPLE_XML_TWO_ARTICLES)

    results = PubMed.search_multiple_authors(["Allen W J"], 2)
    assert len(results.get("Allen W J", [])) == 2


# --- HTTP error handling ---


@responses.activate
def test_HTTP_failure_UIDs():
    responses.add(responses.GET, "https://httpstat.us/500", status=500)
    responses.add(responses.GET, "https://httpstat.us/500", status=500)
    pb = PubMed.PubMed()
    pb.search_url = "https://httpstat.us/500"
    result = pb._get_UIDs_by_author("Hendrix Joe", 1)
    assert result is None


@responses.activate
def test_HTTP_failure_fetch():
    _mock_search(responses, id_list=["12345678"])
    responses.add(responses.GET, FETCH_URL, status=500)

    pb = PubMed.PubMed()
    result = pb.get_publications_by_author("Allen William")
    assert result is None


# --- Post-process filtering (API returns candidates; filter does UT + author match) ---


@responses.activate
def test_filters_non_ut_publications():
    """After post-process filter, non-UT publications are excluded."""
    _mock_search(responses)
    _mock_fetch(responses, xml=SAMPLE_XML_NON_UT)

    pb = PubMed.PubMed()
    result = pb.get_publications_by_author("Smith John", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Smith John")
    assert len(filtered) == 0


@responses.activate
def test_keeps_ut_publications():
    """After post-process filter, UT publications are kept."""
    _mock_search(responses)
    _mock_fetch(responses, xml=SAMPLE_XML_UT)

    pb = PubMed.PubMed()
    result = pb.get_publications_by_author("Allen William", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Allen William")
    assert len(filtered) > 0


@responses.activate
def test_mixed_affiliations_filters_correctly():
    """After post-process filter, only UT-affiliated publication is kept."""
    _mock_search(responses, id_list=["11111111", "22222222"])
    _mock_fetch(responses, xml=SAMPLE_XML_MIXED)

    pb = PubMed.PubMed()
    result = pb.get_publications_by_author("Beavers Kelsey m", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Beavers Kelsey m")
    assert len(filtered) == 1
    assert filtered[0]["title"] == "UT Paper"


@responses.activate
def test_multiple_ut_campuses():
    """After post-process filter, publications from different UT campuses are kept."""
    _mock_search(responses, id_list=["11111111", "22222222"])
    _mock_fetch(responses, xml=SAMPLE_XML_TWO_ARTICLES)

    pb = PubMed.PubMed()
    result = pb.get_publications_by_author("Allen William", rows=10)
    assert result is not None
    filtered = filter_publications_for_author(result, "Allen William")
    assert len(filtered) == 2


# --- Output format ---


@responses.activate
def test_publication_output_format():
    """Verify the output format matches the expected structure."""
    _mock_search(responses)
    _mock_fetch(responses)

    pb = PubMed.PubMed()
    result = pb.get_publications_by_author("Allen William", rows=10)
    assert result is not None
    pub = result[0]
    assert "from" in pub and pub["from"] == "PubMed"
    assert "journal" in pub
    assert "publication_date" in pub
    assert "title" in pub
    assert "authors" in pub
    assert "affiliations" in pub
    assert "doi" in pub
