# Alfred Letterboxd Workflow

Search [Letterboxd](https://letterboxd.com) for films and people directly from Alfred.

## Installation

Download the latest `letterboxd.alfredworkflow` file from the [Releases](https://github.com/jparise/alfred-letterboxd/releases) page and double-click to install.

## Usage

### Film Search

Type `lb` followed by your search query:

```
lb raiders of the lost ark
lb parasite 2019
lb everything everywhere
```

### People Search

Type `lbp` followed by the person's name:

```
lbp harrison ford
lbp greta gerwig
lbp steven spielberg
```

Press **Enter** to open the result in your browser.

## Requirements

**Runtime:**
- Python 3.9+ (included with macOS Monterey and later)

**Checking your Python version:**
```sh
python3 --version  # Should show 3.9 or higher
```

## Development

### Building

```sh
make workflow       # Build Alfred workflow
make install        # Build and install in Alfred
make test           # Run pytest tests and integration tests
make lint           # Lint code with ruff
```

## License

This software is released under the terms of the [MIT License](LICENSE).
