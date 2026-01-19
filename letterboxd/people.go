package letterboxd

import (
	"fmt"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/jparise/alfred-letterboxd/cache"
)

// SearchPeople searches Letterboxd for actors, directors, and other film industry people.
// If cache is provided, results will be cached. Pass nil to disable caching.
func SearchPeople(c *cache.Cache, query string, limit int) ([]Person, error) {
	cacheKey := fmt.Sprintf("people:%s:%d", query, limit)
	if c != nil {
		var people []Person
		if found, _ := c.Get(cacheKey, &people); found {
			return people, nil
		}
	}

	people, err := searchPeople(query, limit)
	if err != nil {
		return nil, err
	}

	if c != nil {
		_ = c.Set(cacheKey, people)
	}

	return people, nil
}

func searchPeople(query string, limit int) ([]Person, error) {
	client := NewClient()

	html, err := client.Search("https://letterboxd.com/s/search/cast-crew/%s/", query)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch search results: %w", err)
	}

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	var people []Person
	doc.Find("li.search-result").Each(func(i int, s *goquery.Selection) {
		if i >= limit {
			return
		}

		person := Person{}

		// Get name and URL
		nameLink := s.Find("a.name")
		if nameLink.Length() > 0 {
			person.Name = strings.TrimSpace(nameLink.Text())
			if href, exists := nameLink.Attr("href"); exists {
				person.URL = fmt.Sprintf("https://letterboxd.com%s", href)
			}
		}

		// Get role (actor, director, etc.)
		roleText := s.Find("small.role").Text()
		if roleText != "" {
			person.Role = strings.ToLower(strings.TrimSpace(roleText))
		}

		// Get known-for films
		s.Find("span.film-title-wrapper a").Each(func(_ int, filmLink *goquery.Selection) {
			filmTitle := strings.TrimSpace(filmLink.Text())
			if filmTitle != "" {
				person.KnownFor = append(person.KnownFor, filmTitle)
			}
		})

		// Only add if we have at least a name
		if person.Name != "" {
			people = append(people, person)
		}
	})

	return people, nil
}
