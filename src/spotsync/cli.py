"""Command-line interface for SpotSync."""

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .parser import M3U8Parser
from .matcher import TrackMatcher
from .spotify_api import SpotifyAPI, SpotifyConfig


app = typer.Typer(help="Synchronize M3U8 playlists with Spotify")
console = Console()


def setup_spotify() -> SpotifyAPI:
    """Setup Spotify API client."""
    try:
        return SpotifyAPI()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Please set the following environment variables:[/yellow]")
        console.print("  - SPOTIFY_CLIENT_ID")
        console.print("  - SPOTIFY_CLIENT_SECRET")
        console.print("  - SPOTIFY_REDIRECT_URI (optional)")
        sys.exit(1)


@app.command()
def sync(
    m3u8_path: Path = typer.Argument(..., help="Path to M3U8 playlist file"),
    playlist_name: Optional[str] = typer.Option(None, "--name", "-n", help="Spotify playlist name (defaults to M3U8 filename)"),
    threshold: float = typer.Option(0.8, "--threshold", "-t", help="Matching confidence threshold (0-1)"),
    public: bool = typer.Option(True, "--public/--private", "-p/-P", help="Make playlist public or private"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear existing playlist before adding tracks"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show what would be done without making changes"),
):
    """Sync an M3U8 playlist file to Spotify."""
    # Parse M3U8 file
    console.print(f"\n[cyan]Parsing M3U8 file:[/cyan] {m3u8_path}")
    parser = M3U8Parser()
    
    try:
        tracks = parser.parse(str(m3u8_path))
    except Exception as e:
        console.print(f"[red]Error parsing M3U8 file: {e}[/red]")
        sys.exit(1)
    
    if not tracks:
        console.print("[yellow]No tracks found in M3U8 file[/yellow]")
        sys.exit(0)
    
    console.print(f"[green]Found {len(tracks)} tracks[/green]")
    
    # Setup Spotify API
    if not dry_run:
        spotify = setup_spotify()
    
    # Determine playlist name
    if playlist_name is None:
        playlist_name = parser.playlist_name or m3u8_path.stem
    
    # Search for tracks on Spotify
    console.print(f"\n[cyan]Searching for tracks on Spotify...[/cyan]")
    
    queries = []
    for track in tracks:
        if track.artist:
            query = f"{track.artist} {track.title}"
        else:
            query = track.title
        queries.append(query)
    
    # Search with progress bar
    search_results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        if not dry_run:
            task = progress.add_task("Searching...", total=len(queries))
            for i, query in enumerate(queries):
                results = spotify.search_track(query, limit=5)
                search_results.append(results)
                progress.update(task, advance=1, description=f"Searching... ({i+1}/{len(queries)})")
        else:
            # In dry-run mode, just show what we would search for
            for track in tracks:
                console.print(f"  Would search for: {track.artist or ''} - {track.title}")
    
    if dry_run:
        console.print(f"\n[yellow]Dry run mode - no changes made[/yellow]")
        return
    
    # Match tracks
    console.print(f"\n[cyan]Matching tracks with threshold {threshold}...[/cyan]")
    matcher = TrackMatcher(threshold=threshold)
    
    local_tracks = [(track.title, track.artist) for track in tracks]
    matches = matcher.find_best_matches(local_tracks, search_results)
    
    # Show matching results
    matched_count = sum(1 for m in matches if m is not None)
    console.print(f"\n[green]Matched {matched_count}/{len(tracks)} tracks[/green]")
    
    if matched_count == 0:
        console.print("[red]No tracks could be matched. Try lowering the threshold.[/red]")
        sys.exit(0)
    
    # Create/update playlist
    console.print(f"\n[cyan]Managing Spotify playlist: '{playlist_name}'[/cyan]")
    
    # Check if playlist exists
    playlist_id = spotify.playlist_exists(playlist_name)
    
    if playlist_id:
        console.print(f"[yellow]Playlist '{playlist_name}' already exists[/yellow]")
        if clear:
            console.print("[yellow]Clearing existing tracks...[/yellow]")
            spotify.clear_playlist(playlist_id)
    else:
        console.print(f"[green]Creating new playlist '{playlist_name}'[/green]")
        playlist_id = spotify.create_playlist(
            name=playlist_name,
            description=f"Imported from {m3u8_path.name}",
            public=public
        )
    
    # Add matched tracks
    track_ids = [match.spotify_id for match in matches if match is not None]
    console.print(f"\n[cyan]Adding {len(track_ids)} tracks to playlist...[/cyan]")
    
    added_count = spotify.add_tracks_to_playlist(playlist_id, track_ids)
    console.print(f"[green]Successfully added {added_count} tracks[/green]")
    
    # Show summary
    if matched_count < len(tracks):
        console.print(f"\n[yellow]Unmatched tracks ({len(tracks) - matched_count}):[/yellow]")
        for i, (track, match) in enumerate(zip(tracks, matches)):
            if match is None:
                console.print(f"  - {track.artist or 'Unknown'} - {track.title}")


@app.command()
def list_tracks(
    m3u8_path: Path = typer.Argument(..., help="Path to M3U8 playlist file"),
):
    """List all tracks in an M3U8 file."""
    parser = M3U8Parser()
    
    try:
        tracks = parser.parse(str(m3u8_path))
    except Exception as e:
        console.print(f"[red]Error parsing M3U8 file: {e}[/red]")
        sys.exit(1)
    
    if not tracks:
        console.print("[yellow]No tracks found in M3U8 file[/yellow]")
        return
    
    # Create a table
    table = Table(title=f"Tracks in {m3u8_path.name}")
    table.add_column("#", style="cyan", no_wrap=True)
    table.add_column("Artist", style="magenta")
    table.add_column("Title", style="green")
    table.add_column("Duration", style="yellow")
    
    for i, track in enumerate(tracks, 1):
        duration = f"{track.duration}s" if track.duration else "-"
        table.add_row(
            str(i),
            track.artist or "-",
            track.title,
            duration
        )
    
    console.print(table)
    console.print(f"\n[cyan]Total tracks: {len(tracks)}[/cyan]")


@app.command()
def test_match(
    m3u8_path: Path = typer.Argument(..., help="Path to M3U8 playlist file"),
    threshold: float = typer.Option(0.8, "--threshold", "-t", help="Matching confidence threshold (0-1)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of tracks to test"),
):
    """Test track matching without creating a playlist."""
    # Parse M3U8 file
    parser = M3U8Parser()
    
    try:
        tracks = parser.parse(str(m3u8_path))[:limit]
    except Exception as e:
        console.print(f"[red]Error parsing M3U8 file: {e}[/red]")
        sys.exit(1)
    
    if not tracks:
        console.print("[yellow]No tracks found in M3U8 file[/yellow]")
        return
    
    # Setup Spotify API
    spotify = setup_spotify()
    matcher = TrackMatcher(threshold=threshold)
    
    console.print(f"\n[cyan]Testing matching for {len(tracks)} tracks with threshold {threshold}[/cyan]\n")
    
    # Test each track
    for track in tracks:
        console.print(f"[cyan]Local track:[/cyan] {track.artist or 'Unknown'} - {track.title}")
        
        # Search on Spotify
        if track.artist:
            query = f"{track.artist} {track.title}"
        else:
            query = track.title
        
        results = spotify.search_track(query, limit=5)
        
        if not results:
            console.print("  [red]No results found[/red]\n")
            continue
        
        # Try to match
        match = matcher.match_track(track.title, track.artist, results)
        
        if match:
            console.print(f"  [green]✓ Matched:[/green] {match.matched_artist} - {match.matched_title}")
            console.print(f"  [yellow]Confidence: {match.confidence:.2%}[/yellow]\n")
        else:
            console.print("  [red]✗ No match found[/red]")
            console.print("  [yellow]Top results:[/yellow]")
            for i, result in enumerate(results[:3], 1):
                artists = ', '.join(a['name'] for a in result['artists'])
                console.print(f"    {i}. {artists} - {result['name']}")
            console.print()


if __name__ == "__main__":
    app()