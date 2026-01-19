package letterboxd

import (
	"fmt"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

// SearchFilms searches Letterboxd for films matching the query.
// If cache is provided, results will be cached. Pass nil to disable caching.
func SearchFilms(c *Cache, query string, limit int) ([]Film, error) {
	cacheKey := fmt.Sprintf("films:%s:%d", query, limit)
	if c != nil {
		var films []Film
		if found, _ := c.Get(cacheKey, &films); found {
			return films, nil
		}
	}

	films, err := searchFilms(query, limit)
	if err != nil {
		return nil, err
	}

	if c != nil {
		_ = c.Set(cacheKey, films)
	}

	return films, nil
}

func searchFilms(query string, limit int) ([]Film, error) {
	client := NewClient()

	html, err := client.Search("https://letterboxd.com/s/search/films/%s/", query)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch search results: %w", err)
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	var films []Film
	doc.Find("li.search-result").Each(func(i int, s *goquery.Selection) {
		if i >= limit {
			return
		}

		film := Film{}

		// Get film data from the react component div
		reactDiv := s.Find("div.react-component")
		if reactDiv.Length() > 0 {
			// Extract film metadata from data attributes
			if slug, exists := reactDiv.Attr("data-item-slug"); exists {
				film.LetterboxdID = slug
				film.URL = fmt.Sprintf("https://letterboxd.com%s", reactDiv.AttrOr("data-item-link", fmt.Sprintf("/film/%s/", slug)))
			}

			// Get title and year from data-item-name (e.g., "The Matrix (1999)")
			if fullName, exists := reactDiv.Attr("data-item-name"); exists {
				film.Title = fullName
				// Parse title and year
				if idx := strings.LastIndex(fullName, " ("); idx != -1 {
					film.Title = fullName[:idx]
					film.Year = strings.Trim(fullName[idx+2:], ")")
				}
			}
		}

		// Get year, director, and other metadata from the text content
		// These are typically in links or spans after the poster
		s.Find("a[href*='/films/year/']").Each(func(_ int, yearLink *goquery.Selection) {
			year := strings.Trim(yearLink.Text(), " ()")
			if film.Year == "" {
				film.Year = year
			}
		})

		// Get directors
		var directors []string
		s.Find("a[href*='/director/']").Each(func(_ int, dirLink *goquery.Selection) {
			director := strings.TrimSpace(dirLink.Text())
			if director != "" {
				directors = append(directors, director)
			}
		})
		if len(directors) > 0 {
			film.Director = strings.Join(directors, ", ")
		}

		// Only add if we have at least a title
		if film.Title != "" {
			films = append(films, film)
		}
	})

	return films, nil
}
