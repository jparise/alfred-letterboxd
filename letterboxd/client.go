// Package letterboxd provides functions for searching Letterboxd.
package letterboxd

import (
	"fmt"
	"io"
	"net/http"
	neturl "net/url"
	"strings"
	"time"
)

// Client handles HTTP requests to Letterboxd.
type Client struct {
	httpClient *http.Client
}

// NewClient creates a new Letterboxd client.
func NewClient() *Client {
	return &Client{
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

// Fetch fetches a URL and returns the response body as a string.
func (c *Client) Fetch(url string) (string, error) {
	req, err := http.NewRequest(http.MethodGet, url, http.NoBody)
	if err != nil {
		return "", err
	}

	req.Header.Add("User-Agent", "Alfred Letterboxd Workflow")
	req.Header.Add("accept", "text/html,application/xhtml+xml,application/xml")
	req.Header.Add("cache-control", "no-cache")
	req.Header.Add("pragma", "no-cache")
	req.Header.Add("sec-ch-ua", "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Google Chrome\";v=\"120\"")
	req.Header.Add("sec-fetch-dest", "document")
	req.Header.Add("sec-fetch-mode", "navigate")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(body), nil
}

// Search builds and fetches a search URL.
func (c *Client) Search(format, query string) (string, error) {
	q := neturl.PathEscape(strings.ToLower(strings.ReplaceAll(query, " ", "+")))
	return c.Fetch(fmt.Sprintf(format, q))
}
