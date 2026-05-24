import http.client
import json
import os
import sys
import time
import urllib.error
from contextlib import contextmanager
from datetime import timedelta
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import lbsearch
from lbsearch import (
    AlfredItem,
    Cache,
    Film,
    LetterboxdClient,
    LetterboxdFilmParser,
    LetterboxdPeopleParser,
    Person,
)


@pytest.fixture
def outputs(monkeypatch):
    """Capture AlfredItem lists passed to alfred_output."""
    calls = []
    monkeypatch.setattr(lbsearch, "alfred_output", calls.append)
    return calls


@pytest.fixture
def urlopen(monkeypatch):
    """Patch urlopen and bypass retry sleeps; return the Mock for configuration."""
    mock = Mock()
    monkeypatch.setattr("urllib.request.urlopen", mock)
    monkeypatch.setattr("time.sleep", lambda *_: None)
    return mock


@pytest.fixture
def client():
    """Mock LetterboxdClient whose .search() can be configured per-test."""
    return Mock()


@contextmanager
def respond_with(body: bytes):
    """A minimal urlopen-style context manager whose .read() returns `body`."""
    yield SimpleNamespace(read=lambda: body)


def http_error(code: int) -> urllib.error.HTTPError:
    """Construct an HTTPError with the given status code."""
    return urllib.error.HTTPError(
        "https://letterboxd.com/s/search/films/q/", code, "", Message(), None
    )


class TestCache:
    def test_init(self, tmp_path):
        """Test cache directory is created"""
        cache = Cache(timedelta(minutes=15), path=tmp_path)
        assert cache.dir.exists()
        assert cache.dir.stat().st_mode & 0o777 == 0o700

    def test_cache_miss(self, tmp_path):
        """Test cache miss returns None"""
        cache = Cache(timedelta(minutes=15), path=tmp_path)
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_hit(self, tmp_path):
        """Test cache hit returns stored value"""
        cache = Cache(timedelta(minutes=15), path=tmp_path)
        items = [AlfredItem(title="Test", subtitle="test", valid=True)]
        cache.set("key", items)
        result = cache.get("key")
        assert result == items

    def test_cache_expiration(self, tmp_path):
        """Test expired cache entries are removed"""
        cache = Cache(timedelta(seconds=1), path=tmp_path)
        items = [AlfredItem(title="Test", subtitle="test", valid=True)]
        cache.set("key", items)

        # Artificially age the file to make it expired
        filepath = cache._key_to_filename("key")
        old_time = time.time() - 2  # 2 seconds ago, exceeds 1 second TTL
        os.utime(filepath, (old_time, old_time))

        result = cache.get("key")
        assert result is None

    def test_prune(self, tmp_path):
        """Test prune removes expired entries"""
        # Create cache with 1 second TTL
        cache = Cache(timedelta(seconds=1), path=tmp_path)
        items = [AlfredItem(title="Test", subtitle="test", valid=True)]
        cache.set("key", items)

        # Verify file exists
        assert len(list(cache.dir.glob("*.json"))) == 1

        # Create another entry and artificially age it by setting mtime to 2 seconds ago
        cache.set("expired", items)
        expired_file = cache._key_to_filename("expired")
        old_time = time.time() - 2  # 2 seconds ago, exceeds 1 second TTL
        os.utime(expired_file, (old_time, old_time))

        # Should have 2 files now
        assert len(list(cache.dir.glob("*.json"))) == 2

        # Prune should remove expired entry
        cache.prune()
        assert len(list(cache.dir.glob("*.json"))) == 1


class TestClientRetry:
    """Test LetterboxdClient.search retry behavior"""

    def test_retry_then_succeed(self, urlopen):
        """A retryable status is retried and can succeed"""
        urlopen.side_effect = [http_error(503), respond_with(b"<html>ok</html>")]
        client = LetterboxdClient()
        assert client.search("http://x/{}/", "q") == "<html>ok</html>"
        assert urlopen.call_count == 2

    def test_non_retryable_status_fails_fast(self, urlopen):
        """A 404 is not retried"""
        urlopen.side_effect = http_error(404)
        client = LetterboxdClient()
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            client.search("http://x/{}/", "q", attempts=3)
        assert exc_info.value.code == 404
        assert urlopen.call_count == 1

    def test_attempts_exhausted(self, urlopen):
        """Persistent retryable failure exhausts attempts and reraises"""
        urlopen.side_effect = http_error(403)
        client = LetterboxdClient()
        with pytest.raises(urllib.error.HTTPError):
            client.search("http://x/{}/", "q", attempts=3)
        assert urlopen.call_count == 3

    def test_http_exception_is_retried(self, urlopen):
        """http.client exceptions (e.g. IncompleteRead) are retried"""
        urlopen.side_effect = [http.client.IncompleteRead(b"partial"), respond_with(b"ok")]
        client = LetterboxdClient()
        assert client.search("http://x/{}/", "q") == "ok"
        assert urlopen.call_count == 2

    def test_attempts_clamped_to_one(self, urlopen):
        """attempts=0 still makes one attempt (no retries)"""
        urlopen.side_effect = http_error(503)
        client = LetterboxdClient()
        with pytest.raises(urllib.error.HTTPError):
            client.search("http://x/{}/", "q", attempts=0)
        assert urlopen.call_count == 1

    def test_fresh_request_per_attempt(self, urlopen):
        """A new urllib Request is built for each attempt"""
        urlopen.side_effect = [
            urllib.error.URLError("boom"),
            respond_with(b"ok"),
        ]
        client = LetterboxdClient()
        client.search("http://x/{}/", "q")
        req_ids = [id(call.args[0]) for call in urlopen.call_args_list]
        assert len(req_ids) == 2
        assert req_ids[0] != req_ids[1]


class TestFilmParser:
    """Test film HTML parsing"""

    @pytest.mark.parametrize(
        "director_html, expected",
        [
            ('<a href="/director/wachowskis/" class="text-slug">Wachowskis</a>', "Wachowskis"),
            ('<a href="/director/wachowskis/">Wachowskis</a>', "Wachowskis"),
            ('<a href="/director/wachowskis/" class="other">Wachowskis</a>', "Wachowskis"),
            (
                '<a href="/director/a/">A</a><a href="/director/b/">B</a>',
                "A, B",
            ),
            ("", ""),
        ],
    )
    def test_parse_film(self, director_html, expected):
        """Test parsing a film search result with various director link forms"""
        html = f"""
        <li class="search-result">
            <div class="react-component"
                 data-item-slug="the-matrix"
                 data-item-name="The Matrix (1999)"
                 data-item-link="/film/the-matrix/">
            </div>
            {director_html}
        </li>
        """
        parser = LetterboxdFilmParser()
        parser.feed(html)

        assert len(parser.films) == 1
        film = parser.films[0]
        assert film.title == "The Matrix"
        assert film.year == "1999"
        assert film.letterboxd_id == "the-matrix"
        assert "letterboxd.com/film/the-matrix" in film.url
        assert film.director == expected


class TestPeopleParser:
    """Test people HTML parsing"""

    def test_parse_person(self):
        """Test parsing a person search result"""
        html = """
        <li class="search-result -contributor -actor">
            <h2 class="title-2"><a href="/actor/keanu-reeves/">Keanu Reeves</a></h2>
            <p class="film-metadata">
                Star of <a href="/film/the-matrix/" class="text-slug">The Matrix</a>
            </p>
        </li>
        """
        parser = LetterboxdPeopleParser()
        parser.feed(html)

        assert len(parser.people) == 1
        person = parser.people[0]
        assert person.name == "Keanu Reeves"
        assert person.role == "actor"
        assert "letterboxd.com/actor/keanu-reeves" in person.url
        assert "The Matrix" in person.known_for


def test_film_as_alfred_item():
    film = Film(
        title="The Matrix",
        year="1999",
        director="Wachowskis",
        url="https://letterboxd.com/film/the-matrix/",
        letterboxd_id="the-matrix",
    )
    item = film.as_alfred_item()

    assert item.get("uid") == "letterboxd-film-the-matrix"
    assert item.get("title") == "The Matrix (1999)"
    assert item.get("subtitle") == "Director: Wachowskis"
    assert item.get("arg") == "https://letterboxd.com/film/the-matrix/"
    assert item.get("text", {}).get("largetype") == "The Matrix"
    assert item.get("valid") is True


def test_person_as_alfred_item():
    person = Person(
        name="Keanu Reeves",
        role="actor",
        known_for=["The Matrix", "John Wick"],
        url="https://letterboxd.com/actor/keanu-reeves/",
    )
    item = person.as_alfred_item()

    assert item.get("uid") == "letterboxd-person-keanu-reeves"
    assert item.get("title") == "Keanu Reeves"
    assert "Actor" in (item.get("subtitle") or "")
    assert "The Matrix" in (item.get("subtitle") or "")
    assert item.get("text", {}).get("largetype") == "Keanu Reeves"
    assert item.get("valid") is True


def test_person_uid_fallback():
    """When url is empty, uid falls back to the person's name"""
    person = Person(name="Keanu Reeves", role="actor", known_for=[], url="")
    item = person.as_alfred_item()
    assert item.get("uid") == "letterboxd-person-Keanu Reeves"


def test_alfred_output(capsys):
    items = [AlfredItem(title="Test", valid=True)]
    lbsearch.alfred_output(items)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "items" in data
    assert len(data["items"]) == 1


def test_search_no_results(client, outputs):
    """Zero results with no search-result <li> reports 'No results found'"""
    client.search.return_value = "<html><body>nothing here</body></html>"
    lbsearch.search(client, "films", "http://test/{}/", "query", LetterboxdFilmParser())
    assert outputs == [
        [{"title": "No results found", "subtitle": 'No films results for "query"', "valid": False}]
    ]


def test_search_format_changed(client, outputs):
    """search-result <li> present but no parsed items signals a format change"""
    # The <li> has the search-result class so saw_result_container is set,
    # but the inner data-item-slug is missing so no Film is produced.
    html = '<li class="search-result"><div class="react-component"></div></li>'
    client.search.return_value = html

    lbsearch.search(client, "films", "http://test/{}/", "query", LetterboxdFilmParser())

    assert len(outputs) == 1 and len(outputs[0]) == 1
    item = outputs[0][0]
    assert item["title"] == "Unable to read Letterboxd search results"
    assert "format has changed" in item["subtitle"]
    assert item["arg"].startswith("https://github.com/jparise/alfred-letterboxd/issues/new?")
    assert "template=search-format.yml" in item["arg"]
    assert "type=films" in item["arg"]
    assert item["valid"] is True


def test_search_http_error(client, outputs):
    """HTTP errors from the client are reported with the status code"""
    client.search.side_effect = http_error(403)
    lbsearch.search(client, "films", "http://test/{}/", "query", LetterboxdFilmParser())
    assert outputs == [
        [{"title": "Error", "subtitle": "Letterboxd returned HTTP 403", "valid": False}]
    ]


def test_search_network_error(client, outputs):
    """URL errors from the client are reported as network errors"""
    client.search.side_effect = urllib.error.URLError("connection refused")
    lbsearch.search(client, "films", "http://test/{}/", "query", LetterboxdFilmParser())
    assert outputs == [
        [{"title": "Error", "subtitle": "Network error: connection refused", "valid": False}]
    ]


def test_search_network_error_collapses_multiline_reason(client, outputs):
    """Multi-line URLError.reason (e.g. SSL errors) is reduced to first line"""
    client.search.side_effect = urllib.error.URLError("first line\nsecond line")
    lbsearch.search(client, "films", "http://test/{}/", "query", LetterboxdFilmParser())
    assert outputs == [
        [{"title": "Error", "subtitle": "Network error: first line", "valid": False}]
    ]


def test_search_http_exception(client, outputs):
    """http.client exceptions (e.g. IncompleteRead) are reported as network errors"""
    client.search.side_effect = http.client.IncompleteRead(b"partial")
    lbsearch.search(client, "films", "http://test/{}/", "query", LetterboxdFilmParser())
    assert outputs == [
        [{"title": "Error", "subtitle": "Network error: IncompleteRead", "valid": False}]
    ]


def test_search_parsing_error(client, outputs):
    """Test that parsing errors are reported to the user"""
    client.search.return_value = "<html>invalid</html>"

    parser = Mock()
    parser.feed.side_effect = Exception("HTML parsing failed")

    lbsearch.search(client, "films", "http://test/{}/", "query", parser)
    assert outputs == [
        [
            {
                "title": "Error",
                "subtitle": "Failed to parse search results: HTML parsing failed",
                "valid": False,
            }
        ]
    ]
