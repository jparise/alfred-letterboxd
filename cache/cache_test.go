package cache

import (
	"os"
	"testing"
	"time"
)

func TestCacheSetAndGet(t *testing.T) {
	cache := newTestCache(t)

	// Set a value
	err := cache.Set("test-key", "test-value")
	if err != nil {
		t.Fatalf("Set failed: %v", err)
	}

	// Get it back
	var value string
	found, err := cache.Get("test-key", &value)
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	if !found {
		t.Fatal("Expected cache hit, got miss")
	}
	if value != "test-value" {
		t.Fatalf("Expected 'test-value', got %q", value)
	}
}

func TestCacheMiss(t *testing.T) {
	cache := newTestCache(t)

	var value string
	found, err := cache.Get("nonexistent", &value)
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	if found {
		t.Fatal("Expected cache miss, got hit")
	}
}

func TestCacheExpiration(t *testing.T) {
	dir := t.TempDir()
	cache := &Cache{dir: dir, ttl: 100 * time.Millisecond}

	err := cache.Set("test-key", "test-value")
	if err != nil {
		t.Fatalf("Set failed: %v", err)
	}

	// Wait for expiration
	time.Sleep(150 * time.Millisecond)

	var value string
	found, err := cache.Get("test-key", &value)
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	if found {
		t.Fatal("Expected cache miss after expiration, got hit")
	}

	// Verify file was cleaned up
	entries, _ := os.ReadDir(dir)
	if len(entries) > 0 {
		t.Fatal("Expected expired entry to be removed")
	}
}

func TestCacheCorruptData(t *testing.T) {
	cache := newTestCache(t)

	// Write corrupt data directly to cache file
	filename := cache.filename("corrupt-key")
	err := os.WriteFile(filename, []byte("not valid json"), 0o600)
	if err != nil {
		t.Fatalf("Failed to write corrupt data: %v", err)
	}

	// Should treat as cache miss
	var value string
	found, err := cache.Get("corrupt-key", &value)
	if err != nil {
		t.Fatalf("Get should not return error for corrupt cache: %v", err)
	}
	if found {
		t.Fatal("Expected cache miss for corrupt data, got hit")
	}

	// Verify corrupt file was cleaned up
	if _, err := os.Stat(filename); !os.IsNotExist(err) {
		t.Fatal("Expected corrupt cache file to be removed")
	}
}

func TestRemoveExpired(t *testing.T) {
	dir := t.TempDir()
	cache := &Cache{dir: dir, ttl: 100 * time.Millisecond}

	// Add some entries
	_ = cache.Set("key1", "value1")
	_ = cache.Set("key2", "value2")

	// Wait for expiration
	time.Sleep(150 * time.Millisecond)

	// Add a fresh entry
	_ = cache.Set("key3", "value3")

	// Remove expired entries
	err := cache.RemoveExpired()
	if err != nil {
		t.Fatalf("RemoveExpired failed: %v", err)
	}

	// Only key3 should remain
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("Expected 1 cache file, got %d", len(entries))
	}

	// Verify key3 still works
	var value string
	found, _ := cache.Get("key3", &value)
	if !found || value != "value3" {
		t.Fatal("Expected key3 to still be cached")
	}
}

func newTestCache(t *testing.T) *Cache {
	t.Helper()
	dir := t.TempDir()
	return &Cache{dir: dir, ttl: 1 * time.Hour}
}
