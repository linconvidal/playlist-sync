# MySpotSync - M3U8 Playlist to Spotify Sync

## **Overview**

MySpotSync is a simple tool to sync .m3u8 playlists with Spotify. It reads one or more .m3u8 files, matches the tracks with Spotify's catalog, and creates/updates corresponding playlists in your Spotify account.

## **Core Features**

1. **Parse .m3u8 files** - Extract track paths and metadata
2. **Match tracks with Spotify** - Find corresponding tracks in Spotify catalog
3. **Sync playlists** - Create/update Spotify playlists based on .m3u8 content
4. **Dual interfaces**:
   - **CLI** - Simple command-line interface for scripting and automation
   - **TUI** - Interactive Textual-based interface for monitoring sync status

## **Architecture**

### Components

1. **M3U8Parser**
   - Read .m3u8 playlist files
   - Extract file paths and EXTINF metadata
   - Support for absolute and relative paths

2. **TrackMatcher**
   - Extract metadata from audio files (artist, title, album)
   - Search Spotify API for matching tracks
   - Use fuzzy matching (≥90% similarity) for best results

3. **SpotifySync**
   - OAuth authentication with Spotify
   - Create playlists if they don't exist
   - Update playlists with matched tracks (batch of 100)
   - Handle rate limiting and API errors

4. **SpotSyncCLI** (Typer CLI)
   - Command-line interface for automation
   - Support for single or batch playlist syncing
   - JSON output option for scripting
   - Dry-run mode for safety

5. **SpotSyncUI** (Textual TUI)
   - Interactive file selection
   - Real-time sync progress
   - Visual display of unmatched tracks

## **Data Flow**

```
.m3u8 files → Parse → Extract metadata → Match with Spotify → Sync playlists
     ↓                      ↓                    ↓                ↓
 File paths          Artist/Title         Track IDs        Updated playlists
```

## **Implementation Details**

### Environment
- Python 3.12 on WSL (Linux)
- Dependencies: spotipy, textual, mutagen (or tinytag), typer, python-Levenshtein

### Spotify API Limits
- 100 tracks per playlist update request
- ~10 requests/second (development mode)
- OAuth scopes: playlist-modify-private, playlist-read-private

### Matching Strategy
- Extract metadata from audio files referenced in .m3u8
- Search Spotify: "{artist} {title}"
- Use Levenshtein distance for fuzzy matching
- Fallback to album/year if multiple matches

## **Usage Flow**

### CLI Mode
```bash
# Sync a single playlist
spotsync sync "My Playlist.m3u8"

# Sync multiple playlists
spotsync sync "Rock.m3u8" "Jazz.m3u8" "Workout.m3u8"

# Sync with custom Spotify playlist name
spotsync sync "My Playlist.m3u8" --name "Awesome Mix Vol. 1"

# Dry run (show what would be synced without making changes)
spotsync sync "My Playlist.m3u8" --dry-run

# Show unmatched tracks only
spotsync check "My Playlist.m3u8"
```

### TUI Mode
1. Launch MySpotSync TUI with `spotsync` or `spotsync tui`
2. Select one or more .m3u8 files
3. Review playlist names (derived from .m3u8 filenames)
4. Start sync process
5. View results and unmatched tracks

## **Setup Steps**

```bash
# Create virtual environment with uv
uv venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install spotipy textual mutagen typer python-Levenshtein

# Register Spotify app at https://developer.spotify.com/dashboard
# Then configure credentials:
export SPOTIPY_CLIENT_ID='your_client_id'
export SPOTIPY_CLIENT_SECRET='your_client_secret'
export SPOTIPY_REDIRECT_URI='http://127.0.0.1:8888/callback'

# Install MySpotSync in development mode
uv pip install -e .

# Run MySpotSync
spotsync                        # Opens TUI
spotsync sync "playlist.m3u8"   # CLI mode
```

## **File Structure**

```
spotsync/
├── __init__.py
├── m3u8_parser.py      # Parse .m3u8 files
├── track_matcher.py    # Match local tracks with Spotify
├── spotify_sync.py     # Spotify API integration
├── cli.py             # CLI interface (using Typer)
├── ui.py              # Textual TUI
├── main.py            # Entry point (routes to CLI or TUI)
├── pyproject.toml     # Package configuration
└── README.md          # Basic documentation
```

## **Error Handling**

- **Unmatched tracks**: Listed in output for manual review
- **API rate limits**: Automatic retry with backoff
- **Invalid file paths**: Skip and report
- **Missing metadata**: Use filename as fallback

## **CLI Examples for Automation**

```bash
# Claude can easily use these commands:

# Quick sync of a playlist
spotsync sync "/path/to/playlist.m3u8"

# Check what would be synced without making changes
spotsync sync "/path/to/playlist.m3u8" --dry-run

# Get JSON output for processing
spotsync sync "/path/to/playlist.m3u8" --json

# Sync and get only summary
spotsync sync "/path/to/playlist.m3u8" --quiet

# Force update (replace entire playlist)
spotsync sync "/path/to/playlist.m3u8" --force
```