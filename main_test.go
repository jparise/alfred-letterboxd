package main

import (
	"testing"

	"github.com/jon/alfred-letterboxd/letterboxd"
)

func TestFormatFilm(t *testing.T) {
	film := letterboxd.Film{
		Title:        "Raiders of the Lost Ark",
		Year:         "1981",
		Director:     "Steven Spielberg",
		URL:          "https://letterboxd.com/film/raiders-of-the-lost-ark/",
		LetterboxdID: "raiders-of-the-lost-ark",
	}

	item := formatFilm(film)

	if item.Title != "Raiders of the Lost Ark (1981)" {
		t.Errorf("Expected title 'Raiders of the Lost Ark (1981)', got %q", item.Title)
	}
	if item.Subtitle != "Director: Steven Spielberg" {
		t.Errorf("Expected subtitle with director, got %q", item.Subtitle)
	}
	if item.UID != "letterboxd-film-raiders-of-the-lost-ark" {
		t.Errorf("Expected UID 'letterboxd-film-raiders-of-the-lost-ark', got %q", item.UID)
	}
	if !item.Valid {
		t.Error("Expected item to be valid")
	}
}

func TestFormatFilmNoDirector(t *testing.T) {
	film := letterboxd.Film{
		Title:        "Unknown Film",
		Year:         "2020",
		URL:          "https://letterboxd.com/film/unknown/",
		LetterboxdID: "unknown",
	}

	item := formatFilm(film)

	if item.Subtitle != "" {
		t.Errorf("Expected empty subtitle, got %q", item.Subtitle)
	}
}

func TestFormatPerson(t *testing.T) {
	person := letterboxd.Person{
		Name:     "Harrison Ford",
		Role:     "actor",
		KnownFor: []string{"Raiders of the Lost Ark", "Star Wars"},
		URL:      "https://letterboxd.com/actor/harrison-ford/",
	}

	item := formatPerson(person)

	if item.Title != "Harrison Ford" {
		t.Errorf("Expected title 'Harrison Ford', got %q", item.Title)
	}
	if item.Subtitle != "Actor • Raiders of the Lost Ark, Star Wars" {
		t.Errorf("Expected subtitle with role and films, got %q", item.Subtitle)
	}
	if !item.Valid {
		t.Error("Expected item to be valid")
	}
}
