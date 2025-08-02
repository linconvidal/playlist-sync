"""Tests for the playlist comparison module."""

import pytest
from spotsync.parser import Track
from spotsync.comparer import PlaylistComparer, ComparisonResult
from spotsync.matcher import TrackMatcher


class TestPlaylistComparer:
    """Test cases for PlaylistComparer class."""
    
    def test_exact_match(self):
        """Test comparison when playlists are identical."""
        comparer = PlaylistComparer()
        
        # Create identical tracks
        local_tracks = [
            Track(title="Song One", artist="Artist A"),
            Track(title="Song Two", artist="Artist B"),
            Track(title="Song Three", artist="Artist C")
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Song One", "artists": "Artist A", "album": "Album 1", "duration_ms": 180000},
            {"id": "2", "name": "Song Two", "artists": "Artist B", "album": "Album 2", "duration_ms": 200000},
            {"id": "3", "name": "Song Three", "artists": "Artist C", "album": "Album 3", "duration_ms": 220000}
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        assert len(result.matched) == 3
        assert len(result.local_only) == 0
        assert len(result.spotify_only) == 0
        assert result.match_percentage == 100.0
    
    def test_completely_different(self):
        """Test comparison when playlists have no overlap."""
        comparer = PlaylistComparer()
        
        local_tracks = [
            Track(title="Local Song One", artist="Local Artist A"),
            Track(title="Local Song Two", artist="Local Artist B")
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Spotify Song One", "artists": "Spotify Artist A", "album": "Album 1", "duration_ms": 180000},
            {"id": "2", "name": "Spotify Song Two", "artists": "Spotify Artist B", "album": "Album 2", "duration_ms": 200000}
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        assert len(result.matched) == 0
        assert len(result.local_only) == 2
        assert len(result.spotify_only) == 2
        assert result.match_percentage == 0.0
    
    def test_partial_match(self):
        """Test comparison with some matching and some different tracks."""
        comparer = PlaylistComparer()
        
        local_tracks = [
            Track(title="Common Song", artist="Common Artist"),
            Track(title="Local Only Song", artist="Local Artist"),
            Track(title="Another Common", artist="Another Artist")
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Common Song", "artists": "Common Artist", "album": "Album 1", "duration_ms": 180000},
            {"id": "2", "name": "Spotify Only Song", "artists": "Spotify Artist", "album": "Album 2", "duration_ms": 200000},
            {"id": "3", "name": "Another Common", "artists": "Another Artist", "album": "Album 3", "duration_ms": 220000}
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        assert len(result.matched) == 2
        assert len(result.local_only) == 1
        assert len(result.spotify_only) == 1
        assert result.local_only[0].title == "Local Only Song"
        assert result.spotify_only[0]["name"] == "Spotify Only Song"
    
    def test_fuzzy_matching(self):
        """Test that fuzzy matching works for slight variations."""
        comparer = PlaylistComparer(TrackMatcher(threshold=0.8))
        
        local_tracks = [
            Track(title="Let It Be", artist="The Beatles"),
            Track(title="Hey Jude", artist="Beatles")  # Missing "The"
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Let it Be", "artists": "The Beatles", "album": "Let It Be", "duration_ms": 180000},  # Different case
            {"id": "2", "name": "Hey Jude", "artists": "The Beatles", "album": "Hey Jude", "duration_ms": 200000}  # Full name
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        # Should match both despite minor differences
        assert len(result.matched) == 2
        assert len(result.local_only) == 0
        assert len(result.spotify_only) == 0
    
    def test_empty_playlists(self):
        """Test edge cases with empty playlists."""
        comparer = PlaylistComparer()
        
        # Both empty
        result = comparer.compare_playlists([], [])
        assert len(result.matched) == 0
        assert len(result.local_only) == 0
        assert len(result.spotify_only) == 0
        assert result.match_percentage == 0.0
        
        # Local empty
        spotify_tracks = [
            {"id": "1", "name": "Song", "artists": "Artist", "album": "Album", "duration_ms": 180000}
        ]
        result = comparer.compare_playlists([], spotify_tracks)
        assert len(result.matched) == 0
        assert len(result.local_only) == 0
        assert len(result.spotify_only) == 1
        
        # Spotify empty
        local_tracks = [Track(title="Song", artist="Artist")]
        result = comparer.compare_playlists(local_tracks, [])
        assert len(result.matched) == 0
        assert len(result.local_only) == 1
        assert len(result.spotify_only) == 0
    
    def test_duplicate_handling(self):
        """Test handling of duplicate tracks."""
        comparer = PlaylistComparer()
        
        # Local has duplicates
        local_tracks = [
            Track(title="Song", artist="Artist"),
            Track(title="Song", artist="Artist"),  # Duplicate
            Track(title="Different Song", artist="Artist")
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Song", "artists": "Artist", "album": "Album", "duration_ms": 180000},
            {"id": "2", "name": "Different Song", "artists": "Artist", "album": "Album", "duration_ms": 200000}
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        # Should match first occurrence, second becomes local_only
        assert len(result.matched) == 2
        assert len(result.local_only) == 1
        assert result.local_only[0].title == "Song"  # The duplicate
    
    def test_artist_variations(self):
        """Test matching with artist name variations."""
        comparer = PlaylistComparer(TrackMatcher(threshold=0.83))
        
        local_tracks = [
            Track(title="Song", artist="Artist feat. Guest"),
            Track(title="Another Song", artist="Main Artist & Collaborator")
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Song", "artists": "Artist, Guest", "album": "Album 1", "duration_ms": 180000},
            {"id": "2", "name": "Another Song", "artists": "Main Artist, Collaborator", "album": "Album 2", "duration_ms": 200000}
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        # Should match despite featuring/collaboration format differences
        assert len(result.matched) >= 1  # At least one should match
    
    def test_case_insensitive_matching(self):
        """Test that matching is case insensitive."""
        comparer = PlaylistComparer()
        
        local_tracks = [
            Track(title="SONG IN CAPS", artist="ARTIST NAME"),
            Track(title="song in lower", artist="artist name")
        ]
        
        spotify_tracks = [
            {"id": "1", "name": "Song In Caps", "artists": "Artist Name", "album": "Album 1", "duration_ms": 180000},
            {"id": "2", "name": "SONG IN LOWER", "artists": "ARTIST NAME", "album": "Album 2", "duration_ms": 200000}
        ]
        
        result = comparer.compare_playlists(local_tracks, spotify_tracks)
        
        # Should match both regardless of case
        assert len(result.matched) == 2
        assert len(result.local_only) == 0
        assert len(result.spotify_only) == 0