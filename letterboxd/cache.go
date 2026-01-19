package letterboxd

import (
	"crypto/md5"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Cache handles caching of search results to disk.
type Cache struct {
	dir string
	ttl time.Duration
}

type cacheEntry struct {
	Data      json.RawMessage `json:"data"`
	ExpiresAt time.Time       `json:"expires_at"`
}

// NewCache creates a new cache instance. Uses Alfred's cache directory if available
// and falls back to a system temporary directory.
func NewCache(ttl time.Duration) (*Cache, error) {
	cacheDir := os.Getenv("alfred_workflow_cache")
	if cacheDir == "" {
		cacheDir = filepath.Join(os.TempDir(), "alfred-letterboxd-cache")
	}

	if err := os.MkdirAll(cacheDir, 0o700); err != nil {
		return nil, fmt.Errorf("failed to create cache directory: %w", err)
	}

	cache := &Cache{dir: cacheDir, ttl: ttl}

	// Clean up expired entries opportunistically
	_ = cache.RemoveExpired()

	return cache, nil
}

// Get retrieves a cached value if it exists and hasn't expired.
func (c *Cache) Get(key string, value any) (bool, error) {
	filename := c.filename(key)

	data, err := os.ReadFile(filename)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil // Cache miss
		}
		return false, err
	}

	var entry cacheEntry
	if err := json.Unmarshal(data, &entry); err != nil {
		_ = os.Remove(filename)
		return false, nil //nolint:nilerr // Intentionally return nil to treat corrupt cache as a miss
	}

	if time.Now().After(entry.ExpiresAt) {
		_ = os.Remove(filename)
		return false, nil
	}

	if err := json.Unmarshal(entry.Data, value); err != nil {
		_ = os.Remove(filename)
		return false, nil //nolint:nilerr // Intentionally return nil to treat corrupt cache as a miss
	}

	return true, nil
}

// Set stores a value in the cache with TTL.
func (c *Cache) Set(key string, value any) error {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal value: %w", err)
	}

	entry := cacheEntry{
		Data:      data,
		ExpiresAt: time.Now().Add(c.ttl),
	}

	entryData, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("failed to marshal cache entry: %w", err)
	}

	filename := c.filename(key)
	if err := os.WriteFile(filename, entryData, 0o600); err != nil {
		return fmt.Errorf("failed to write cache file: %w", err)
	}

	return nil
}

// RemoveExpired removes all expired cache entries from disk.
func (c *Cache) RemoveExpired() error {
	entries, err := os.ReadDir(c.dir)
	if err != nil {
		return err
	}

	now := time.Now()
	for _, dirEntry := range entries {
		if dirEntry.IsDir() {
			continue
		}

		filename := filepath.Join(c.dir, dirEntry.Name())
		data, err := os.ReadFile(filename)
		if err != nil {
			continue // Skip files we can't read
		}

		var entry cacheEntry
		if err := json.Unmarshal(data, &entry); err != nil {
			// Remove corrupt entries
			_ = os.Remove(filename)
			continue
		}

		if now.After(entry.ExpiresAt) {
			_ = os.Remove(filename)
		}
	}

	return nil
}

// filename generates a cache filename from a key.
func (c *Cache) filename(key string) string {
	hash := md5.Sum([]byte(key))
	return filepath.Join(c.dir, fmt.Sprintf("%x.json", hash))
}
