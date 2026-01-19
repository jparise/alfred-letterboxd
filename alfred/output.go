// Package alfred provides utilities for formatting Alfred Script Filter JSON output.
package alfred

import (
	"encoding/json"
	"fmt"
)

// Icon represents an icon in Alfred results.
type Icon struct {
	Path string `json:"path,omitempty"`
}

// Item represents a single result item in Alfred's Script Filter format.
type Item struct {
	UID          string `json:"uid"`
	Title        string `json:"title"`
	Subtitle     string `json:"subtitle"`
	Arg          string `json:"arg"`
	Autocomplete string `json:"autocomplete,omitempty"`
	Icon         Icon   `json:"icon"`
	Valid        bool   `json:"valid"`
}

// Response represents the complete Alfred Script Filter JSON response.
type Response struct {
	Items []Item `json:"items"`
}

// Output marshals items to JSON and prints to stdout.
func Output(items []Item) {
	response := Response{Items: items}

	jsonBytes, err := json.MarshalIndent(response, "", "  ")
	if err != nil {
		response = Response{Items: []Item{{
			Title:    "Error",
			Subtitle: fmt.Sprintf("Failed to format results: %v", err),
			Valid:    false,
		}}}
		jsonBytes, _ = json.MarshalIndent(response, "", "  ")
	}

	fmt.Println(string(jsonBytes))
}

// OutputItems formats and outputs items as Alfred JSON using the provided formatter.
func OutputItems[T any](items []T, formatter func(T) Item) {
	alfredItems := make([]Item, 0, len(items))
	for _, item := range items {
		alfredItems = append(alfredItems, formatter(item))
	}
	Output(alfredItems)
}

// OutputMessage outputs a single Alfred item containing a message for the user.
func OutputMessage(title, subtitle string) {
	item := Item{
		Title:    title,
		Subtitle: subtitle,
		Valid:    false,
	}
	Output([]Item{item})
}

// OutputErrorf outputs a formatted error message as an Alfred item.
func OutputErrorf(format string, a ...any) {
	OutputMessage("Error", fmt.Sprintf(format, a...))
}
