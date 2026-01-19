import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import lbsearch


class TestCache:
    def test_init(self, tmp_path):
        """Test cache directory is created"""
        cache = lbsearch.Cache(timedelta(minutes=15), path=tmp_path)
        assert cache.dir.exists()
        assert cache.dir.stat().st_mode & 0o777 == 0o700

    def test_cache_miss(self, tmp_path):
        """Test cache miss returns None"""
        cache = lbsearch.Cache(timedelta(minutes=15), path=tmp_path)
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_hit(self, tmp_path):
        """Test cache hit returns stored value"""
        cache = lbsearch.Cache(timedelta(minutes=15), path=tmp_path)
        items = [{"title": "Test", "subtitle": "test", "valid": True}]
        cache.set("key", items)
        result = cache.get("key")
        assert result == items

    def test_cache_expiration(self, tmp_path):
        """Test expired cache entries are removed"""
        cache = lbsearch.Cache(timedelta(seconds=1), path=tmp_path)
        items = [{"title": "Test", "subtitle": "test", "valid": True}]
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
        cache = lbsearch.Cache(timedelta(seconds=1), path=tmp_path)
        items = [{"title": "Test", "subtitle": "test", "valid": True}]
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


class TestFilmParser:
    """Test film HTML parsing"""

    def test_parse_film(self):
        """Test parsing a film search result"""
        html = """
        <li class="search-result">
            <div class="react-component"
                 data-item-slug="the-matrix"
                 data-item-name="The Matrix (1999)"
                 data-item-link="/film/the-matrix/">
            </div>
            <a href="/director/wachowskis/">Wachowskis</a>
        </li>
        """
        parser = lbsearch.LetterboxdFilmParser()
        parser.feed(html)

        assert len(parser.films) == 1
        film = parser.films[0]
        assert film.title == "The Matrix"
        assert film.year == "1999"
        assert film.letterboxd_id == "the-matrix"
        assert "letterboxd.com/film/the-matrix" in film.url


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
        parser = lbsearch.LetterboxdPeopleParser()
        parser.feed(html)

        assert len(parser.people) == 1
        person = parser.people[0]
        assert person.name == "Keanu Reeves"
        assert person.role == "actor"
        assert "letterboxd.com/actor/keanu-reeves" in person.url
        assert "The Matrix" in person.known_for


def test_film_as_item():
    film = lbsearch.Film(
        title="The Matrix",
        year="1999",
        director="Wachowskis",
        url="https://letterboxd.com/film/the-matrix/",
        letterboxd_id="the-matrix",
    )
    item = film.as_item()

    assert item["uid"] == "letterboxd-film-the-matrix"
    assert item["title"] == "The Matrix (1999)"
    assert item["subtitle"] == "Director: Wachowskis"
    assert item["arg"] == "https://letterboxd.com/film/the-matrix/"
    assert item["valid"] is True


def test_person_as_item():
    person = lbsearch.Person(
        name="Keanu Reeves",
        role="actor",
        known_for=["The Matrix", "John Wick"],
        url="https://letterboxd.com/actor/keanu-reeves/",
    )
    item = person.as_item()

    assert item["uid"] == "letterboxd-person-Keanu Reeves"
    assert item["title"] == "Keanu Reeves"
    assert "Actor" in item["subtitle"]
    assert "The Matrix" in item["subtitle"]
    assert item["valid"] is True


def test_alfred_output(capsys):
    items = [{"title": "Test", "valid": True}]
    lbsearch.alfred_output(items)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "items" in data
    assert len(data["items"]) == 1
