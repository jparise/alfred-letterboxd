# Alfred Letterboxd Workflow

Search [Letterboxd](https://letterboxd.com) for films and people directly from Alfred.

## Installation

Download the latest `.alfredworkflow` file from the [Releases](https://github.com/jparise/alfred-letterboxd/releases) page and double-click to install.

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

## Development

### Building

```sh
make build          # Build binary
make workflow       # Build Alfred workflow
make install        # Build and install in Alfred
make test           # Run tests
make lint           # Run linter
```

### Release Process

1. Create and push a git tag:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push --tags
   ```

2. GitHub Actions will automatically build and publish the release

## License

MIT License
