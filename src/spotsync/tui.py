"""Terminal User Interface for SpotSync."""

import sys
import json
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, DataTable, Input, Label, Static, LoadingIndicator, Header, Footer, DirectoryTree, ProgressBar, Checkbox
from textual.screen import Screen
from textual.reactive import reactive
from rich.text import Text

from .parser import M3U8Parser, Track
from .matcher import TrackMatcher, MatchResult
from .spotify_api import SpotifyAPI


@dataclass
class TrackMatch:
    """Container for track and its match result."""
    local_track: Track
    match_result: Optional[MatchResult] = None
    selected: bool = True


def get_config_path() -> Path:
    """Get the path to the config file."""
    config_dir = Path.home() / ".spotsync"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def load_last_directory() -> str:
    """Load the last used directory from config."""
    try:
        config_path = get_config_path()
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                last_dir = config.get('last_directory', '/')
                # Verify the directory still exists
                if Path(last_dir).exists():
                    return last_dir
    except Exception:
        pass
    return "/"


def save_last_directory(directory: str) -> None:
    """Save the last used directory to config."""
    try:
        config_path = get_config_path()
        config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        
        config['last_directory'] = directory
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass  # Silently fail if we can't save config


class FileSelectionScreen(Screen):
    """Screen for selecting M3U8 files."""
    
    CSS = """
    FileSelectionScreen {
        background: $surface;
    }
    
    .file-browser-container {
        height: 20;
        border: solid $primary;
        margin: 1;
    }
    
    .file-controls {
        height: 8;
        padding: 1;
        border: solid $primary;
    }
    
    DirectoryTree {
        background: $surface;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.selected_file: Optional[Path] = None
        self.current_directory: str = load_last_directory()
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        
        with Container(classes="file-browser-container"):
            yield DirectoryTree(
                self.current_directory,
                id="file-tree"
            )
        
        with Container(classes="file-controls"):
            yield Label("Click on an M3U8 file above, then click 'Select File' to continue")
            with Horizontal():
                yield Button("Select File", variant="primary", id="select-file-button", disabled=True)
                yield Button("Reset to /", variant="default", id="reset-dir-button")
                yield Button("Cancel", variant="default", id="cancel-button")
        
        yield Static("Browse and select your M3U8 playlist file", id="status")
        yield Footer()
    
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in the directory tree."""
        file_path = Path(event.path)
        
        # Save the current directory
        save_last_directory(str(file_path.parent))
        
        # Check if it's an M3U8 file
        if file_path.suffix.lower() in ['.m3u', '.m3u8']:
            self.selected_file = file_path
            self.query_one("#select-file-button", Button).disabled = False
            status = self.query_one("#status", Static)
            status.update(f"Selected: {file_path.name}")
        else:
            self.selected_file = None
            self.query_one("#select-file-button", Button).disabled = True
            status = self.query_one("#status", Static)
            status.update(f"Please select an M3U8 file (selected: {file_path.name})")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-file-button" and self.selected_file:
            # Return to main app with selected file
            await self.app.load_selected_file(str(self.selected_file))
            self.app.pop_screen()
        elif event.button.id == "reset-dir-button":
            # Reset directory tree to root directory
            root_dir = "/"
            self.current_directory = root_dir
            save_last_directory(root_dir)
            # Refresh the directory tree
            tree = self.query_one("#file-tree", DirectoryTree)
            tree.path = root_dir
            tree.reload()
            self.selected_file = None
            self.query_one("#select-file-button", Button).disabled = True
            status = self.query_one("#status", Static)
            status.update("Directory reset to /. Browse and select your M3U8 playlist file")
        elif event.button.id == "cancel-button":
            self.app.pop_screen()



class SpotSyncApp(App):
    """Main SpotSync TUI application."""
    
    TITLE = "SpotSync - M3U8 to Spotify Playlist Converter"
    CSS = """
    SpotSyncApp {
        background: $surface;
    }
    
    .header-container {
        height: 3;
        background: $primary;
        padding: 1;
    }
    
    .file-input-container {
        height: 8;
        padding: 1;
        border: solid $primary;
    }
    
    .tracks-container {
        border: solid $primary;
        height: 1fr;
        margin: 1;
    }
    
    .controls-container {
        height: 18;
        padding: 1;
        border: solid $primary;
    }
    
    .label-spacing {
        margin-right: 1;
        min-width: 15;
    }
    
    Checkbox {
        margin: 0 2;
        padding: 0 1;
    }
    
    Checkbox > .toggle--label {
        color: $text;
        text-style: bold;
    }
    
    Checkbox:focus > .toggle--label {
        color: $accent;
    }
    
    .status-bar {
        height: 1;
        background: $accent;
        color: $text;
        text-align: center;
    }
    
    Button {
        margin: 0 1;
    }
    
    #file-display {
        width: 1fr;
        max-width: 50;
    }
    
    LoadingIndicator {
        background: transparent;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.tracks: List[TrackMatch] = []
        self.spotify: Optional[SpotifyAPI] = None
        self.matcher = TrackMatcher(threshold=0.83)  # Slightly lowered to catch edge cases like features
        self.playlist_name = ""
        self.selected_file_path: Optional[str] = None
        
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        
        with Container(classes="file-input-container"):
            yield Label("M3U8 File:")
            with Horizontal():
                yield Static("No file selected", id="file-display")
                yield Button("Browse...", variant="primary", id="browse-button")
                yield Button("Load", variant="success", id="load-button", disabled=True)
        
        with ScrollableContainer(classes="tracks-container"):
            yield DataTable(id="tracks-table")
        
        with Container(classes="controls-container"):
            with Horizontal():
                yield Label("Playlist Name:", classes="label-spacing")
                yield Input(placeholder="Enter Spotify playlist name...", id="playlist-input")
            yield Static("")  # Spacer
            yield ProgressBar(id="progress-bar", show_eta=False, show_percentage=True)
            yield Static("")  # Spacer
            with Horizontal():
                yield Checkbox("Replace entire playlist (delete missing tracks)", id="replace-mode", value=False)
            yield Static("")  # Spacer
            with Horizontal():
                yield Button("Search & Match", variant="primary", id="match-button", disabled=True)
                yield Button("Create Playlist", variant="success", id="create-button", disabled=True)
                yield Button("Select All", id="select-all-button")
                yield Button("Select None", id="select-none-button")
        
        yield Static("Ready", classes="status-bar", id="status")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the tracks table."""
        table = self.query_one("#tracks-table", DataTable)
        table.add_columns("✓", "Artist", "Title", "Match", "Confidence")
        table.cursor_type = "row"
        
        # Hide progress bar initially
        progress = self.query_one("#progress-bar", ProgressBar)
        progress.display = False
        
        # Try to initialize Spotify
        try:
            self.spotify = SpotifyAPI()
            self.update_status("Spotify connected", "green")
        except Exception as e:
            self.update_status(f"Spotify error: {str(e)}", "red")
    
    def update_status(self, message: str, style: str = "white") -> None:
        """Update the status bar."""
        status = self.query_one("#status", Static)
        status.update(Text(message, style=style))
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "browse-button":
            self.push_screen(FileSelectionScreen())
        elif event.button.id == "load-button":
            await self.load_m3u8()
        elif event.button.id == "match-button":
            await self.match_tracks()
        elif event.button.id == "create-button":
            await self.create_playlist()
        elif event.button.id == "select-all-button":
            self.select_all_tracks(True)
        elif event.button.id == "select-none-button":
            self.select_all_tracks(False)
    
    async def load_selected_file(self, file_path: str) -> None:
        """Called when a file is selected from the file browser."""
        self.selected_file_path = file_path
        
        # Update the display
        file_display = self.query_one("#file-display", Static)
        file_display.update(Path(file_path).name)
        
        # Enable the load button
        self.query_one("#load-button", Button).disabled = False
        
        self.update_status(f"File selected: {Path(file_path).name}", "green")
    
    async def load_m3u8(self) -> None:
        """Load and parse M3U8 file."""
        if not self.selected_file_path:
            self.update_status("Please select a file first", "yellow")
            return
        
        file_path = self.selected_file_path
        
        try:
            self.update_status("Loading M3U8 file...", "cyan")
            parser = M3U8Parser()
            tracks = parser.parse(file_path)
            
            if not tracks:
                self.update_status("No tracks found in file", "yellow")
                return
            
            # Store tracks and update playlist name
            self.tracks = [TrackMatch(track) for track in tracks]
            self.playlist_name = parser.playlist_name or Path(file_path).stem
            
            # Update playlist input
            playlist_input = self.query_one("#playlist-input", Input)
            playlist_input.value = self.playlist_name
            
            # Update table
            self.update_tracks_table()
            
            # Enable match button
            self.query_one("#match-button", Button).disabled = False
            
            self.update_status(f"Loaded {len(tracks)} tracks", "green")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
    
    def update_tracks_table(self) -> None:
        """Update the tracks table display."""
        table = self.query_one("#tracks-table", DataTable)
        table.clear()
        
        for track_match in self.tracks:
            track = track_match.local_track
            match = track_match.match_result
            
            check = "✓" if track_match.selected else " "
            artist = track.artist or "-"
            title = track.title
            
            if match:
                match_text = f"{match.matched_artist} - {match.matched_title}"
                confidence = f"{match.confidence:.0%}"
                row_style = "green" if match.confidence >= 0.9 else "yellow"
            else:
                match_text = "-"
                confidence = "-"
                row_style = "dim"
            
            table.add_row(check, artist, title, match_text, confidence)
    
    async def match_tracks(self) -> None:
        """Search and match tracks on Spotify."""
        if not self.spotify:
            self.update_status("Spotify not connected", "red")
            return
        
        if not self.tracks:
            self.update_status("No tracks loaded", "yellow")
            return
        
        self.update_status(f"Searching for {len(self.tracks)} tracks...", "cyan")
        
        # Show and initialize progress bar
        progress = self.query_one("#progress-bar", ProgressBar)
        progress.display = True
        progress.update(total=len(self.tracks), progress=0)
        
        # Disable buttons during search
        self.query_one("#match-button", Button).disabled = True
        self.query_one("#create-button", Button).disabled = True
        
        try:
            # Build search queries
            queries = []
            for track_match in self.tracks:
                track = track_match.local_track
                if track.artist:
                    query = f"{track.artist} {track.title}"
                else:
                    query = track.title
                queries.append(query)
            
            # Search in batches
            matched_count = 0
            for i, track_match in enumerate(self.tracks):
                query = queries[i]
                results = self.spotify.search_track(query, limit=10)  # Increased limit
                
                if results:
                    match = self.matcher.match_track(
                        track_match.local_track.title,
                        track_match.local_track.artist,
                        results
                    )
                    if match:
                        track_match.match_result = match
                        matched_count += 1
                    else:
                        # Try alternative search strategies for unmatched tracks
                        track = track_match.local_track
                        alternative_match = None
                        
                        # Try search with just the title
                        if track.artist and not alternative_match:
                            title_only_results = self.spotify.search_track(track.title, limit=10)
                            if title_only_results:
                                alternative_match = self.matcher.match_track(
                                    track.title, track.artist, title_only_results
                                )
                        
                        # Try search with cleaned title (remove special chars)
                        if not alternative_match:
                            import re
                            cleaned_title = re.sub(r'[^\w\s]', '', track.title)
                            if cleaned_title != track.title:
                                clean_query = f"{track.artist} {cleaned_title}" if track.artist else cleaned_title
                                clean_results = self.spotify.search_track(clean_query, limit=10)
                                if clean_results:
                                    alternative_match = self.matcher.match_track(
                                        track.title, track.artist, clean_results
                                    )
                        
                        if alternative_match:
                            track_match.match_result = alternative_match
                            matched_count += 1
                            print(f"DEBUG: Alternative match found for '{query}': {alternative_match.matched_artist} - {alternative_match.matched_title}")
                        else:
                            # Debug: Log unmatched tracks with detailed scoring
                            print(f"DEBUG: No match for '{query}' - Got {len(results)} results")
                            if results and len(results) > 0:
                                for j, result in enumerate(results[:3]):  # Show top 3
                                    artist_name = result.get('artists', [{}])[0].get('name', 'Unknown')
                                    track_name = result.get('name', 'Unknown')
                                    print(f"  Result {j+1}: {artist_name} - {track_name}")
                                    
                                    # Calculate and show the score manually for debugging
                                    from Levenshtein import ratio
                                    title_score = ratio(track.title.lower(), track_name.lower())
                                    artist_score = ratio(track.artist.lower() if track.artist else "", artist_name.lower()) if track.artist else 0
                                    if track.artist and artist_score < 0.6:
                                        total_score = (title_score * 0.4) + (artist_score * 0.6)
                                    else:
                                        total_score = (title_score * 0.6) + (artist_score * 0.4) if track.artist else title_score
                                    print(f"    Title: {title_score:.2f}, Artist: {artist_score:.2f}, Total: {total_score:.2f} (threshold: 0.85)")
                else:
                    print(f"DEBUG: No search results for '{query}'")
                
                # Update progress bar and status
                progress.update(progress=i+1)
                self.update_status(f"Searching... {i+1}/{len(self.tracks)} (matched: {matched_count})", "cyan")
                
                # Allow UI to update every few tracks
                if i % 3 == 0:  # Update UI every 3 tracks for more responsive feedback
                    self.update_tracks_table()  # Update table to show new matches
                    self.refresh()  # Force refresh of the UI
                    import asyncio
                    await asyncio.sleep(0.01)  # Brief yield to allow UI update
            
            # Update table with results
            self.update_tracks_table()
            
            # Hide progress bar
            progress.display = False
            
            # Enable create button if we have matches
            if matched_count > 0:
                self.query_one("#create-button", Button).disabled = False
            
            self.update_status(f"Matched {matched_count}/{len(self.tracks)} tracks", "green")
            
            # Show notification with results
            self.notify(f"Track matching complete: {matched_count}/{len(self.tracks)} tracks matched", severity="information")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
            self.notify(f"Error during matching: {str(e)}", severity="error")
        finally:
            # Hide progress bar and re-enable buttons
            progress = self.query_one("#progress-bar", ProgressBar)
            progress.display = False
            self.query_one("#match-button", Button).disabled = False
    
    async def create_playlist(self) -> None:
        """Create Spotify playlist with matched tracks."""
        if not self.spotify:
            self.update_status("Spotify not connected", "red")
            return
        
        # Get selected tracks with matches
        selected_matches = [
            tm for tm in self.tracks 
            if tm.selected and tm.match_result is not None
        ]
        
        if not selected_matches:
            self.update_status("No matched tracks selected", "yellow")
            return
        
        playlist_input = self.query_one("#playlist-input", Input)
        playlist_name = playlist_input.value.strip() or self.playlist_name
        
        if not playlist_name:
            self.update_status("Please enter a playlist name", "yellow")
            return
        
        # Get configuration options
        replace_mode = self.query_one("#replace-mode", Checkbox).value
        public_mode = True  # Always create public playlists
        
        try:
            self.update_status("Creating playlist...", "cyan")
            
            # Check if playlist exists
            playlist_id = self.spotify.playlist_exists(playlist_name)
            
            if playlist_id:
                # Playlist exists
                if replace_mode:
                    self.update_status(f"Replacing playlist '{playlist_name}'...", "cyan")
                    self.notify(f"Replacing entire playlist: {playlist_name}", severity="warning")
                else:
                    self.update_status(f"Adding to existing playlist '{playlist_name}'...", "cyan")
                    self.notify(f"Updating existing playlist: {playlist_name}", severity="information")
            else:
                # Create new playlist (always public)
                playlist_id = self.spotify.create_playlist(
                    name=playlist_name,
                    description="Created by SpotSync",
                    public=True
                )
                self.update_status(f"Created playlist '{playlist_name}'", "green")
                self.notify(f"Successfully created playlist: {playlist_name}", severity="information")
            
            # Handle tracks based on mode
            track_ids = [tm.match_result.spotify_id for tm in selected_matches]
            
            if replace_mode and playlist_id:
                # Replace entire playlist
                added_count = self.spotify.replace_playlist_tracks(playlist_id, track_ids)
            else:
                # Add tracks to playlist
                added_count = self.spotify.add_tracks_to_playlist(playlist_id, track_ids)
            
            # Update status based on mode
            if replace_mode:
                self.update_status(
                    f"Replaced playlist '{playlist_name}' with {added_count} tracks", 
                    "green"
                )
                self.notify(
                    f"Successfully replaced '{playlist_name}' with {added_count} tracks", 
                    severity="information"
                )
            else:
                self.update_status(
                    f"Added {added_count} tracks to '{playlist_name}'", 
                    "green"
                )
                self.notify(
                    f"Successfully added {added_count} tracks to '{playlist_name}'", 
                    severity="information"
                )
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
            self.notify(f"Error creating playlist: {str(e)}", severity="error")
    
    def select_all_tracks(self, select: bool) -> None:
        """Select or deselect all tracks."""
        for track_match in self.tracks:
            track_match.selected = select
        self.update_tracks_table()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the tracks table."""
        if 0 <= event.cursor_row < len(self.tracks):
            # Toggle selection
            self.tracks[event.cursor_row].selected = not self.tracks[event.cursor_row].selected
            self.update_tracks_table()


def main():
    """Run the TUI application."""
    app = SpotSyncApp()
    app.run()


if __name__ == "__main__":
    main()