"""Playlist comparison module for comparing M3U8 with Spotify playlists."""

from dataclasses import dataclass
from typing import List, Tuple, Set, Optional, Dict, Any
from .parser import Track
from .matcher import TrackMatcher


@dataclass
class ComparisonResult:
    """Results of playlist comparison."""
    local_only: List[Track]  # Tracks only in M3U8
    spotify_only: List[Dict[str, Any]]  # Tracks only in Spotify
    matched: List[Tuple[Track, Dict[str, Any]]]  # Matched pairs
    total_local: int
    total_spotify: int
    match_percentage: float


class PlaylistComparer:
    """Compare local M3U8 playlists with Spotify playlists."""
    
    def __init__(self, matcher: Optional[TrackMatcher] = None):
        """Initialize with optional custom matcher.
        
        Args:
            matcher: Custom TrackMatcher instance. If None, uses default with threshold 0.83
        """
        self.matcher = matcher or TrackMatcher(threshold=0.83)
    
    def compare_playlists(
        self, 
        local_tracks: List[Track], 
        spotify_tracks: List[Dict[str, Any]]
    ) -> ComparisonResult:
        """Compare local M3U8 tracks with Spotify playlist tracks.
        
        Args:
            local_tracks: List of Track objects from M3U8Parser
            spotify_tracks: List of track dicts from Spotify API
            
        Returns:
            ComparisonResult with detailed differences
        """
        # Initialize result containers
        matched_pairs = []
        local_only = []
        spotify_only = []
        
        # Track which Spotify tracks have been matched
        matched_spotify_ids = set()
        
        # Try to match each local track with a Spotify track using TrackMatcher
        for local_track in local_tracks:
            # Convert Spotify tracks to the format expected by TrackMatcher
            spotify_results = []
            for spotify_track in spotify_tracks:
                # Skip if already matched
                if spotify_track['id'] in matched_spotify_ids:
                    continue
                
                # Convert to TrackMatcher format
                track_result = {
                    'id': spotify_track['id'],
                    'name': spotify_track['name'],
                    'artists': [{'name': artist.strip()} for artist in spotify_track['artists'].split(',')]
                }
                spotify_results.append(track_result)
            
            # Use TrackMatcher to find the best match
            match_result = self.matcher.match_track(
                local_track.title, 
                local_track.artist, 
                spotify_results
            )
            
            if match_result:
                # Find the original Spotify track using the matched ID
                matched_spotify_track = None
                for spotify_track in spotify_tracks:
                    if spotify_track['id'] == match_result.spotify_id:
                        matched_spotify_track = spotify_track
                        break
                
                if matched_spotify_track:
                    matched_pairs.append((local_track, matched_spotify_track))
                    matched_spotify_ids.add(match_result.spotify_id)
                else:
                    local_only.append(local_track)
            else:
                local_only.append(local_track)
        
        # Find Spotify tracks that weren't matched
        for spotify_track in spotify_tracks:
            if spotify_track['id'] not in matched_spotify_ids:
                spotify_only.append(spotify_track)
        
        # Calculate match percentage
        # Count total unique tracks considering both playlists
        total_unique = len(local_tracks) + len(spotify_only)
        match_percentage = (len(matched_pairs) / total_unique * 100) if total_unique > 0 else 0.0
        
        return ComparisonResult(
            local_only=local_only,
            spotify_only=spotify_only,
            matched=matched_pairs,
            total_local=len(local_tracks),
            total_spotify=len(spotify_tracks),
            match_percentage=match_percentage
        )