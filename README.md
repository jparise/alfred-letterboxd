# Alfred Letterboxd Workflow

Search [Letterboxd](https://letterboxd.com) for films and people directly from [Alfred](https://www.alfredapp.com/).

[⤓ Install on the Alfred Gallery](https://alfred.app/workflows/jparise/letterboxd-search/)

## Usage

Search for films using the `lb` keyword.

![Film Search](images/lb.png)

* <kbd>↩</kbd> Open the result page in your default browser.
* <kbd>⌘</kbd><kbd>Y</kbd> Quick Look the result page.

Search for people using the `lbp` keyword.

![People Search](images/lbp.png)

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
