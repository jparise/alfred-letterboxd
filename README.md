# Alfred Letterboxd Workflow

Search [Letterboxd](https://letterboxd.com) for films and people directly from [Alfred](https://www.alfredapp.com/).

## Installation

Download the latest `letterboxd.alfredworkflow` file from the [Releases](https://github.com/jparise/alfred-letterboxd/releases/latest) page and double-click to install.

## Usage

### Film Search

Type `lb` followed by your search query to search films:

```
lb raiders of the lost ark
lb parasite 2019
lb everything everywhere
```

![lb.png](lb.png)

### People Search

Type `lbp` followed by the person's name to search cast and crew:

```
lbp harrison ford
lbp greta gerwig
lbp steven spielberg
```

![lbp.png](lbp.png)

### Configuration

In the workflow's configuration, you can customize the search keywords. This is
useful if you have keyword conflicts with other workflows or prefer different
keywords.

## Requirements

- [Alfred Powerpack](https://www.alfredapp.com/powerpack/)
- Python 3.9+ (included with macOS Ventura and later)

```sh
python3 --version  # Should show 3.9 or higher
```

## Custom Web Search

Alternatively, you can get a simpler (less integrated) Letterboxd search experience without
installing a full workflow using a [Custom Web Search](https://www.alfredapp.com/help/features/web-search/#custom):

[`alfred://customsearch/Search%20Letterboxd%20for%20'%7Bquery%7D'/letterboxd/utf8/nospace/https://letterboxd.com/search/?q=%7Bquery%7D`][cws]

[cws]: alfred://customsearch/Search%20Letterboxd%20for%20'%7Bquery%7D'/letterboxd/utf8/nospace/https://letterboxd.com/search/?q=%7Bquery%7D

## Development

### Building

```sh
make workflow       # Build Alfred workflow
make install        # Build and install in Alfred
make test           # Run tests
make lint           # Lint code
```

## License

This software is released under the terms of the [MIT License](LICENSE).
