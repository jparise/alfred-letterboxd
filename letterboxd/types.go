package letterboxd

// Film represents a movie from Letterboxd.
type Film struct {
	Title        string
	Year         string
	Director     string
	URL          string
	Genres       []string
	LetterboxdID string
}

// Person represents an actor, director, or other film industry person.
type Person struct {
	Name      string
	Role      string // e.g., "actor", "director", "cinematography"
	FilmCount string // e.g., "Star of 136 films"
	KnownFor  []string
	URL       string
}
