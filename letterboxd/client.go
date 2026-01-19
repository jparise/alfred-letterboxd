// Package letterboxd provides functions for searching Letterboxd.
package letterboxd

import (
	"fmt"
	"io"
	"net/http"
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
			Timeout: 10 * time.Second,
		},
	}
}

// FetchWithRetry fetches a URL with retry logic.
func (c *Client) FetchWithRetry(url string, maxRetries int) (string, error) {
	var lastErr error

	for i := 0; i <= maxRetries; i++ {
		resp, err := c.httpClient.Get(url)
		if err != nil {
			lastErr = err
			time.Sleep(time.Duration(i+1) * 100 * time.Millisecond)
			continue
		}

		if resp.StatusCode != http.StatusOK {
			resp.Body.Close()
			lastErr = fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
			time.Sleep(time.Duration(i+1) * 100 * time.Millisecond)
			continue
		}

		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			lastErr = err
			continue
		}

		return string(body), nil
	}

	return "", fmt.Errorf("failed after %d retries: %w", maxRetries, lastErr)
}
