# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SpotSync is a Python tool designed to synchronize M3U8 playlist files with Spotify using fuzzy matching for track identification. The project is fully implemented with all core features functional.

## Architecture

The application follows a modular architecture with five core components:

1. **M3U8 Parser** - Handles reading and parsing M3U8 playlist files
2. **Track Matcher** - Uses fuzzy matching to identify tracks on Spotify
3. **Spotify API Layer** - Manages all Spotify API interactions
4. **CLI Interface** - Command-line interface for automation
5. **TUI Interface** - Terminal UI for interactive use

## Technology Stack

- Python 3.12+
- UV (package manager)
- Textual (TUI framework)
- Typer (CLI framework)
- Spotipy (Spotify API wrapper)
- python-Levenshtein (fuzzy matching)

## Development Commands

```bash
# Package management
uv sync                      # Install dependencies
uv pip install -e .         # Install in development mode

# Running the application
uv run spotsync             # Run TUI interface (no args)
uv run spotsync sync file.m3u8  # Sync M3U8 to Spotify
uv run spotsync list-tracks file.m3u8  # List tracks in M3U8
uv run spotsync test-match file.m3u8   # Test matching without creating playlist
uv run python -m spotsync   # Alternative way to run TUI

# Testing
uv run pytest               # Run all tests
uv run pytest -v            # Run tests with verbose output
uv run pytest --cov=spotsync  # Run with coverage
```

## Key Implementation Considerations

1. **Spotify Authentication**: Uses OAuth2 flow with required scopes: `playlist-read-private`, `playlist-read-collaborative`, `playlist-modify-public`, `playlist-modify-private`

2. **Fuzzy Matching Strategy**: 
   - Clean track metadata (remove special characters, normalize case)
   - Try exact match first
   - Fall back to fuzzy matching with configurable threshold
   - Handle featuring artists and remixes

3. **Error Handling**: The design emphasizes graceful error handling for:
   - Invalid M3U8 files
   - Spotify API rate limiting
   - Network issues
   - Track matching failures

4. **Data Flow**:
   - Parse M3U8 → Extract track info → Search Spotify → Match tracks → Create/update playlist

## Project Structure

```
playlist-sync/
├── src/
│   └── spotsync/
│       ├── __init__.py       # Package initialization
│       ├── __main__.py       # Main entry point
│       ├── parser.py         # M3U8 parsing logic
│       ├── matcher.py        # Track matching with fuzzy logic
│       ├── spotify_api.py    # Spotify API integration
│       ├── cli.py            # CLI interface with Typer
│       └── tui.py            # TUI interface with Textual
├── tests/
│   ├── __init__.py
│   ├── test_parser.py        # Parser module tests
│   └── test_matcher.py       # Matcher module tests
├── pyproject.toml            # Project configuration
├── uv.lock                   # Dependency lock file
├── CLAUDE.md                 # This file
└── README.MD                 # Project documentation
```

## Current Status

✅ **FULLY IMPLEMENTED** - All core features are complete and functional:

- **M3U8 Parser**: Handles various M3U8 formats with EXTINF support
- **Track Matcher**: Fuzzy matching with configurable threshold (default 0.8)
- **Spotify API**: OAuth2 authentication with full playlist management
- **CLI Interface**: Three commands (`sync`, `list-tracks`, `test-match`)
- **TUI Interface**: Interactive terminal UI with file browser and track selection
- **Tests**: 16 passing tests with comprehensive coverage

## Environment Setup

Before using SpotSync, configure your Spotify API credentials. You can either:

### Option 1: Use a .env file (Recommended)

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual Spotify app credentials:
   ```bash
   SPOTIFY_CLIENT_ID=your_actual_client_id
   SPOTIFY_CLIENT_SECRET=your_actual_client_secret
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

### Option 2: Use environment variables

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
export SPOTIFY_REDIRECT_URI="http://127.0.0.1:8888/callback"  # Optional
```

**Note**: The redirect URI must use `127.0.0.1` (not `localhost`) to comply with Spotify's security requirements.

## Usage Examples

```bash
# Sync an M3U8 file to Spotify (CLI)
uv run spotsync sync my_playlist.m3u8 --name "My Spotify Playlist"

# List tracks in an M3U8 file
uv run spotsync list-tracks my_playlist.m3u8

# Test matching without creating playlist
uv run spotsync test-match my_playlist.m3u8 --threshold 0.7

# Interactive TUI mode
uv run spotsync
```

## Recent Improvements & Known Issues

### TUI Interface Debugging (Fixed)
- **Issue**: TUI interface not reflecting code changes despite reinstalls
- **Root Cause**: Multiple problems in screen architecture and CSS layout
- **Solution**: 
  1. Consolidated MainScreen functionality into SpotSyncApp directly
  2. Fixed CSS container heights (.file-input-container: 8, .controls-container: 10)
  3. Limited #file-display width (max-width: 50) to prevent button overflow

### Directory Persistence (Implemented)
- **Feature**: Last visited directory is saved to `~/.spotsync/config.json`
- **Benefit**: File browser remembers last location (e.g., `/Volumes/hd/root/music/albums`)

### Track Matching Algorithm Improvements (Fixed)
- **Issue**: False matches and missing matches due to metadata inconsistencies
- **Problems Found**:
  1. Threshold too low (0.7) caused false positives like "Kwasu Asante" matching "Jalen Ngonda"
  2. String cleaning function too aggressive, removing remix information
  3. Feature duplicates in titles causing score drops

- **Solutions Applied**:
  1. **Optimal threshold**: Set to 0.83 (balances accuracy vs coverage)
  2. **Improved string cleaning**: Preserves remix/feature info before removing brackets/parentheses
  3. **Better artist weighting**: Penalizes bad artist matches (< 60% similarity)

### Matching Strategy Details
- **Current threshold**: 0.83 (83% similarity required)
- **Weighting**: Title 60% + Artist 40% (normal), Title 40% + Artist 60% (penalty for bad artist match)
- **String cleaning**: Extracts and preserves "remix", "mix", "edit", "version", "rework" keywords
- **Alternative searches**: Title-only and cleaned-title fallbacks for unmatched tracks

### Common Metadata Issues
- **Name variations**: "Kwasu" vs "Kwaku" - requires manual M3U8 correction
- **Feature formatting**: "[Cabu & Ta-ku Remix]" vs "- Cabu & Ta-ku Remix" - handled by improved cleaning
- **Duplicate features**: "(feat. Daniel Caesar)" when artist already includes "Daniel Caesar" - handled by threshold adjustment

### Debugging Commands
```bash
# Debug specific matching issues
uv run spotsync test-match file.m3u8 --threshold 0.83 --limit 10

# Test matching with dry-run mode
uv run spotsync sync file.m3u8 --dry-run

# Check what's in a playlist
uv run spotsync list-tracks file.m3u8
```