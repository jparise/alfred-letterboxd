package letterboxd

import (
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/jon/alfred-letterboxd/cache"
)

// SearchPeople searches Letterboxd for actors, directors, and other film industry people.
func SearchPeople(query string, limit int) ([]Person, error) {
	// Initialize cache with 15 minute TTL
	c, err := cache.New(15 * time.Minute)
	if err != nil {
		// If cache fails, continue without it
		return searchPeopleUncached(query, limit)
	}

	// Try to get from cache
	cacheKey := fmt.Sprintf("people:%s:%d", query, limit)
	var people []Person
	if found, _ := c.Get(cacheKey, &people); found {
		return people, nil
	}

	// Cache miss, fetch from Letterboxd
	people, err = searchPeopleUncached(query, limit)
	if err != nil {
		return nil, err
	}

	// Store in cache (ignore errors)
	_ = c.Set(cacheKey, people)

	return people, nil
}

func searchPeopleUncached(query string, limit int) ([]Person, error) {
	client := NewClient()

	// URL encode the query and construct search URL
	encodedQuery := url.PathEscape(strings.ToLower(strings.ReplaceAll(query, " ", "+")))
	searchURL := fmt.Sprintf("https://letterboxd.com/s/search/cast-crew/%s/", encodedQuery)

	// Fetch HTML
	html, err := client.FetchWithRetry(searchURL, 2)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch search results: %w", err)
	}

	// Parse HTML
	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	var people []Person

	// Find people results
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
