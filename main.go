// Command lbsearch provides a CLI tool for searching Letterboxd films and people.
package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/jparise/alfred-letterboxd/alfred"
	"github.com/jparise/alfred-letterboxd/letterboxd"
	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

const version = "dev"

var (
	showVersion = flag.Bool("version", false, "Show version information")
	titleCaser  = cases.Title(language.English)
)

func init() {
	flag.Usage = printHelp
}

func printHelp() {
	help := `Letterboxd search tool for Alfred

Usage:
  lbsearch [options] <command> [<query>]

Commands:
  films <query>     Search for films
  people <query>    Search for people (actors, directors, etc.)

Options:
  -version          Show version information

Examples:
  lbsearch films raiders of the lost ark
  lbsearch films parasite 2019
  lbsearch people harrison ford

For use with Alfred:
  This tool is designed to be used with the Alfred Letterboxd workflow.
  It outputs results in Alfred's Script Filter JSON format.`

	fmt.Println(help)
}

func main() {
	flag.Parse()

	if *showVersion {
		fmt.Println(version)
		return
	}

	args := flag.Args()
	if len(args) < 1 {
		printHelp()
		os.Exit(1)
	}

	// Get query for search commands
	var query string
	if len(args) >= 2 {
		query = strings.Join(args[1:], " ")
	}
	if strings.TrimSpace(query) == "" {
		alfred.OutputMessage("Search Letterboxd", "Type a film title or person's name to search...")
		return
	}

	// Initialize cache with 15 minute TTL
	c, err := letterboxd.NewCache(15 * time.Minute)
	if err != nil {
		// If cache initialization fails, continue without it
		c = nil
	}

	searchType := args[0]
	switch searchType {
	case "films":
		searchFilms(c, query)
	case "people":
		searchPeople(c, query)
	default:
		alfred.OutputErrorf("Unknown command: %s", searchType)
		return
	}
}

func searchFilms(c *letterboxd.Cache, query string) {
	films, err := letterboxd.SearchFilms(c, query, 10)
	if err != nil {
		alfred.OutputErrorf("Failed to search films: %v", err)
		return
	}

	if len(films) == 0 {
		outputNoResults(query)
		return
	}

	alfred.OutputItems(films, formatFilm)
}

func searchPeople(c *letterboxd.Cache, query string) {
	people, err := letterboxd.SearchPeople(c, query, 10)
	if err != nil {
		alfred.OutputErrorf("Failed to search people: %v", err)
		return
	}

	if len(people) == 0 {
		outputNoResults(query)
		return
	}

	alfred.OutputItems(people, formatPerson)
}

func outputNoResults(query string) {
	alfred.OutputMessage(
		"No results found",
		fmt.Sprintf("No results for %q", query),
	)
}

func formatFilm(film letterboxd.Film) alfred.Item {
	// Build title with year
	title := film.Title
	if film.Year != "" {
		title = fmt.Sprintf("%s (%s)", film.Title, film.Year)
	}

	// Build subtitle with director
	var subtitle string
	if film.Director != "" {
		subtitle = fmt.Sprintf("Director: %s", film.Director)
	}

	return alfred.Item{
		UID:          fmt.Sprintf("letterboxd-film-%s", film.LetterboxdID),
		Title:        title,
		Subtitle:     subtitle,
		Arg:          film.URL,
		Autocomplete: film.Title,
		Icon:         alfred.Icon{Path: "icon.png"},
		Valid:        true,
	}
}

func formatPerson(person letterboxd.Person) alfred.Item {
	var subtitleParts []string
	if person.Role != "" {
		subtitleParts = append(subtitleParts, titleCaser.String(person.Role))
	}
	if len(person.KnownFor) > 0 {
		subtitleParts = append(subtitleParts, strings.Join(person.KnownFor, ", "))
	}

	return alfred.Item{
		UID:          fmt.Sprintf("letterboxd-person-%s", person.Name),
		Title:        person.Name,
		Subtitle:     strings.Join(subtitleParts, " • "),
		Arg:          person.URL,
		Autocomplete: person.Name,
		Icon:         alfred.Icon{Path: "icon.png"},
		Valid:        true,
	}
}
