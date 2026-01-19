package letterboxd

// Film represents a movie from Letterboxd.
type Film struct {
	Title        string
	Year         string
	Director     string
	URL          string
	LetterboxdID string
}

// Person represents an actor, director, or other film industry person.
type Person struct {
	Name     string
	Role     string // e.g., "actor", "director", "cinematography"
	KnownFor []string
	URL      string
}
