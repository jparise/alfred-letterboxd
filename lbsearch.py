#!/usr/bin/env python3
"""Letterboxd search tool for Alfred"""

import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple, Optional, Protocol, Type, TypedDict, Union

__version__ = "0.0.0"


class AlfredIcon(TypedDict):
    path: str


class AlfredItem(TypedDict, total=False):
    uid: str
    title: str
    subtitle: str
    valid: bool
    arg: str
    autocomplete: str
    icon: AlfredIcon


class AsItem(Protocol):
    def as_item(self) -> AlfredItem: ...


@dataclass
class Film(AsItem):
    title: str
    year: str
    director: str
    url: str
    letterboxd_id: str

    def as_item(self) -> AlfredItem:
        title = f"{self.title} ({self.year})" if self.year else self.title
        subtitle = f"Director: {self.director}" if self.director else ""

        return {
            "uid": f"letterboxd-film-{self.letterboxd_id}",
            "title": title,
            "subtitle": subtitle,
            "arg": self.url,
            "autocomplete": self.title,
            "icon": {"path": "icon.png"},
            "valid": True,
        }


@dataclass
class Person(AsItem):
    name: str
    role: str
    known_for: list[str]
    url: str

    def as_item(self) -> AlfredItem:
        parts = []
        if self.role:
            parts.append(self.role.title())
        if self.known_for:
            parts.append(", ".join(self.known_for))

        return {
            "uid": f"letterboxd-person-{self.name}",
            "title": self.name,
            "subtitle": " • ".join(parts),
            "arg": self.url,
            "autocomplete": self.name,
            "icon": {"path": "icon.png"},
            "valid": True,
        }


class LetterboxdParser(HTMLParser):
    @property
    def results(self) -> list[AsItem]: ...


class LetterboxdFilmParser(LetterboxdParser):
    """HTML parser for Letterboxd film search results"""

    films: list[Film]
    current_film: Optional[Film]
    directors: list[str]

    def __init__(self):
        super().__init__()
        self.films = []
        self.in_result = False
        self.current_film = None
        self.in_director_link = False
        self.directors = []

    @property
    def results(self) -> list[Film]:
        return self.films

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Check if we're entering a search result
        if tag == "li" and "search-result" in attrs_dict.get("class", ""):
            self.in_result = True
            self.current_film = Film(title="", year="", director="", url="", letterboxd_id="")
            self.directors = []

        # Extract film data from react component
        if self.in_result and tag == "div" and "react-component" in attrs_dict.get("class", ""):
            slug = attrs_dict.get("data-item-slug", "")
            name = attrs_dict.get("data-item-name", "")
            link = attrs_dict.get("data-item-link", f"/film/{slug}/")

            if slug:
                self.current_film.letterboxd_id = slug
                self.current_film.url = f"https://letterboxd.com{link}"

                # Parse title and year from "Title (YEAR)"
                if name and " (" in name:
                    idx = name.rfind(" (")
                    self.current_film.title = name[:idx]
                    self.current_film.year = name[idx + 2 : -1]
                elif name:
                    self.current_film.title = name

        # Track director links - look for text-slug class
        if self.in_result and tag == "a":
            href = attrs_dict.get("href", "")
            classes = attrs_dict.get("class", "")
            if "/director/" in href and "text-slug" in classes:
                self.in_director_link = True

    def handle_endtag(self, tag):
        if tag == "li" and self.in_result:
            # Finalize current film
            if self.current_film and self.current_film.title:
                self.current_film.director = ", ".join(self.directors)
                self.films.append(self.current_film)
            self.in_result = False
            self.current_film = None
            self.directors = []

        if tag == "a" and self.in_director_link:
            self.in_director_link = False

    def handle_data(self, data):
        if self.in_director_link:
            if director := data.strip():
                self.directors.append(director)


class LetterboxdPeopleParser(LetterboxdParser):
    """HTML parser for Letterboxd people search results"""

    people: list[Person]
    current_person: Optional[Person]

    def __init__(self):
        super().__init__()
        self.people = []
        self.in_result = False
        self.current_person = None
        self.in_name_link = False
        self.in_film_link = False

    @property
    def results(self) -> list[Person]:
        return self.people

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Check if we're entering a search result - extract role from class
        if tag == "li" and "search-result" in attrs_dict.get("class", ""):
            self.in_result = True
            classes = attrs_dict.get("class", "")
            # Extract role from class like "-actor", "-director"
            role = ""
            if "-actor" in classes:
                role = "actor"
            elif "-director" in classes:
                role = "director"
            elif "-producer" in classes:
                role = "producer"
            elif "-writer" in classes:
                role = "writer"
            self.current_person = Person(name="", role=role, known_for=[], url="")

        # Track name link in h2
        if self.in_result and tag == "a":
            href = attrs_dict.get("href", "")
            classes = attrs_dict.get("class", "")
            # First link in h2 is the person's name
            if href and not self.current_person.url:
                self.in_name_link = True
                self.current_person.url = f"https://letterboxd.com{href}"
            # Film links have text-slug class
            elif "text-slug" in classes:
                self.in_film_link = True

    def handle_endtag(self, tag):
        if tag == "li" and self.in_result:
            # Finalize current person
            if self.current_person and self.current_person.name:
                self.people.append(self.current_person)
            self.in_result = False
            self.current_person = None

        if tag == "a":
            if self.in_name_link:
                self.in_name_link = False
            if self.in_film_link:
                self.in_film_link = False

    def handle_data(self, data):
        if self.in_name_link and self.current_person:
            self.current_person.name = data.strip()
        elif self.in_film_link and self.current_person:
            if film := data.strip():
                self.current_person.known_for.append(film)


class Cache:
    """File-based cache with TTL management"""

    def __init__(self, ttl: timedelta, path: Union[Path, str, None] = None):
        self.dir = Path(
            path
            or os.getenv("alfred_workflow_cache")
            or os.path.join(tempfile.gettempdir(), "alfred-letterboxd")
        )
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.ttl = ttl

    def __repr__(self) -> str:
        return f"Cache(dir='{self.dir}', ttl={self.ttl})"

    def _key_to_filename(self, key: str) -> Path:
        hash_obj = hashlib.md5(key.encode())
        return self.dir / f"{hash_obj.hexdigest()}.json"

    def _is_expired(self, filepath: Path) -> bool:
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        return datetime.now() - mtime > self.ttl

    def get(self, key: str) -> Optional[list[AlfredItem]]:
        path = self._key_to_filename(key)
        try:
            if self._is_expired(path):
                path.unlink(missing_ok=True)
                return None
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def set(self, key: str, items: list[AlfredItem]):
        path = self._key_to_filename(key)
        with open(path, "w") as f:
            json.dump(items, f)

    def prune(self):
        """Remove expired cache entries"""
        try:
            for path in self.dir.iterdir():
                if not (path.is_file() and path.suffix == ".json"):
                    continue
                if self._is_expired(path):
                    path.unlink(missing_ok=True)
        except OSError:
            pass


class LetterboxdClient:
    """HTTP client for Letterboxd searches"""

    def __init__(self, timeout: float = 5):
        self.headers = {
            "User-Agent": f"Alfred Letterboxd Workflow/{__version__}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
        }
        self.timeout = timeout

    def search(self, format_url: str, query: str) -> str:
        url = format_url.format(urllib.parse.quote_plus(query.lower()))
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return response.read().decode("utf-8")


def alfred_output(items: list[AlfredItem]):
    response = {"items": items}
    print(json.dumps(response, indent=2))


def alfred_error(message: str):
    alfred_output([{"title": "Error", "subtitle": message, "valid": False}])


def alfred_message(title: str, subtitle: str):
    alfred_output([{"title": title, "subtitle": subtitle, "valid": False}])


def search(
    client: LetterboxdClient,
    typ: str,
    url_pattern: str,
    query: str,
    parser: LetterboxdParser,
    limit: int = 10,
    cache: Optional[Cache] = None,
):
    cache_key = f"{typ}:{query}:{limit}"
    if cache is not None:
        if cached := cache.get(cache_key):
            alfred_output(cached)
            return

    html = client.search(url_pattern, query)
    parser.feed(html)

    items = [f.as_item() for f in parser.results[:limit]]
    if not items:
        alfred_message("No results found", f'No {typ} results for "{query}"')
        return

    if cache is not None:
        cache.set(cache_key, items)

    alfred_output(items)


class SearchSpec(NamedTuple):
    url_pattern: str
    parser: Type[LetterboxdParser]


SEARCH_SPECS: dict[str, SearchSpec] = {
    "films": SearchSpec(
        "https://letterboxd.com/s/search/films/{}/",
        LetterboxdFilmParser,
    ),
    "people": SearchSpec(
        "https://letterboxd.com/s/search/cast-crew/{}/",
        LetterboxdPeopleParser,
    ),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-cache", dest="cache", action="store_false", help="disable the cache")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("type", choices=SEARCH_SPECS, help="Search type")
    parser.add_argument("query", help="Search query")

    args = parser.parse_args()

    if not args.query:
        alfred_output([])
        return

    client = LetterboxdClient()

    cache = None
    if args.cache:
        try:
            cache = Cache(timedelta(minutes=15))
        except Exception:
            cache = None

    spec = SEARCH_SPECS.get(args.type)
    if not spec:
        alfred_error(f"Unsupported search type: {args.type}")
        return

    try:
        search(
            client,
            args.type,
            spec.url_pattern,
            args.query,
            spec.parser(),
            cache=cache,
        )
    except Exception as e:
        alfred_error(f"Search failed: {e}")

    if cache is not None:
        cache.prune()


if __name__ == "__main__":
    main()
