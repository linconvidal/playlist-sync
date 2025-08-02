"""Spotify API integration module."""

import os
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv


@dataclass
class SpotifyConfig:
    """Configuration for Spotify API."""
    client_id: str
    client_secret: str
    redirect_uri: str = "http://127.0.0.1:8888/callback"
    scope: str = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"


class SpotifyAPI:
    """Handles all Spotify API interactions."""
    
    def __init__(self, config: Optional[SpotifyConfig] = None):
        """Initialize Spotify API client.
        
        Args:
            config: SpotifyConfig object. If None, reads from environment variables.
        """
        # Load environment variables from .env file if it exists
        load_dotenv()
        
        if config is None:
            config = SpotifyConfig(
                client_id=os.getenv('SPOTIFY_CLIENT_ID', ''),
                client_secret=os.getenv('SPOTIFY_CLIENT_SECRET', ''),
                redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8888/callback')
            )
        
        if not config.client_id or not config.client_secret:
            raise ValueError("Spotify client ID and secret must be provided")
        
        self.config = config
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scope=config.scope
        ))
        self._user_id = None
    
    @property
    def user_id(self) -> str:
        """Get the current user's ID."""
        if self._user_id is None:
            self._user_id = self.sp.current_user()['id']
        return self._user_id
    
    def search_track(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks on Spotify.
        
        Args:
            query: Search query (can include artist and track name)
            limit: Maximum number of results to return
            
        Returns:
            List of track objects from Spotify API
        """
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            return results['tracks']['items']
        except Exception as e:
            print(f"Error searching for track '{query}': {e}")
            return []
    
    def search_tracks_batch(self, queries: List[str], limit: int = 10) -> List[List[Dict]]:
        """Search for multiple tracks in sequence.
        
        Args:
            queries: List of search queries
            limit: Maximum number of results per query
            
        Returns:
            List of result lists for each query
        """
        results = []
        for query in queries:
            tracks = self.search_track(query, limit)
            results.append(tracks)
        return results
    
    def get_user_playlists(self, limit: int = 50) -> List[Dict]:
        """Get the current user's playlists.
        
        Args:
            limit: Maximum number of playlists to return
            
        Returns:
            List of playlist objects
        """
        playlists = []
        offset = 0
        
        while True:
            results = self.sp.current_user_playlists(limit=50, offset=offset)
            playlists.extend(results['items'])
            
            if not results['next'] or len(playlists) >= limit:
                break
            
            offset += 50
        
        return playlists[:limit]
    
    def playlist_exists(self, name: str) -> Optional[str]:
        """Check if a playlist with the given name exists.
        
        Args:
            name: Playlist name to search for
            
        Returns:
            Playlist ID if found, None otherwise
        """
        playlists = self.get_user_playlists()
        for playlist in playlists:
            if playlist['name'] == name:
                return playlist['id']
        return None
    
    def create_playlist(self, name: str, description: str = "", public: bool = True) -> str:
        """Create a new playlist.
        
        Args:
            name: Playlist name
            description: Playlist description
            public: Whether the playlist should be public
            
        Returns:
            ID of the created playlist
        """
        playlist = self.sp.user_playlist_create(
            user=self.user_id,
            name=name,
            public=public,
            description=description
        )
        return playlist['id']
    
    def get_playlist_tracks(self, playlist_id: str) -> Set[str]:
        """Get all track IDs in a playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            Set of track IDs
        """
        tracks = set()
        offset = 0
        
        while True:
            results = self.sp.playlist_tracks(playlist_id, offset=offset)
            
            for item in results['items']:
                if item['track'] and item['track']['id']:
                    tracks.add(item['track']['id'])
            
            if not results['next']:
                break
            
            offset += 100
        
        return tracks
    
    def get_playlist_tracks_detailed(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get detailed track information from a Spotify playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of dicts with keys: 'id', 'name', 'artists', 'album', 'duration_ms'
        """
        tracks = []
        offset = 0
        
        while True:
            results = self.sp.playlist_tracks(playlist_id, offset=offset)
            
            for item in results['items']:
                track = item['track']
                if track and track['id']:
                    track_info = {
                        'id': track['id'],
                        'name': track['name'],
                        'artists': ', '.join(artist['name'] for artist in track['artists']),
                        'album': track['album']['name'],
                        'duration_ms': track['duration_ms']
                    }
                    tracks.append(track_info)
            
            if not results['next']:
                break
            
            offset += 100
        
        return tracks
    
    def find_playlist_by_name(self, name: str) -> Optional[str]:
        """Find a user's playlist by exact name match.
        
        Args:
            name: Playlist name to search for
            
        Returns:
            Playlist ID if found, None otherwise
        """
        # Reuse existing playlist_exists method which already does this
        return self.playlist_exists(name)
    
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str], 
                              check_duplicates: bool = True) -> int:
        """Add tracks to a playlist.
        
        Args:
            playlist_id: Spotify playlist ID
            track_ids: List of Spotify track IDs to add
            check_duplicates: Whether to check for duplicates before adding
            
        Returns:
            Number of tracks actually added
        """
        if not track_ids:
            return 0
        
        # Filter out duplicates if requested
        if check_duplicates:
            existing_tracks = self.get_playlist_tracks(playlist_id)
            track_ids = [tid for tid in track_ids if tid not in existing_tracks]
        
        if not track_ids:
            return 0
        
        # Spotify API limits to 100 tracks per request
        added_count = 0
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i + 100]
            try:
                self.sp.playlist_add_items(playlist_id, batch)
                added_count += len(batch)
            except Exception as e:
                print(f"Error adding tracks to playlist: {e}")
                break
        
        return added_count
    
    def clear_playlist(self, playlist_id: str) -> None:
        """Remove all tracks from a playlist.
        
        Args:
            playlist_id: Spotify playlist ID
        """
        # Get all tracks
        track_ids = list(self.get_playlist_tracks(playlist_id))
        
        if not track_ids:
            return
        
        # Remove in batches of 100
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i + 100]
            self.sp.playlist_remove_all_occurrences_of_items(playlist_id, batch)
    
    def replace_playlist_tracks(self, playlist_id: str, track_ids: List[str]) -> int:
        """Replace all tracks in a playlist with new tracks.
        
        Args:
            playlist_id: Spotify playlist ID
            track_ids: List of Spotify track IDs to set as the playlist content
            
        Returns:
            Number of tracks added to the playlist
        """
        # First clear the playlist
        self.clear_playlist(playlist_id)
        
        # Then add the new tracks
        return self.add_tracks_to_playlist(playlist_id, track_ids, check_duplicates=False)
    
    def update_playlist_details(self, playlist_id: str, name: Optional[str] = None,
                               description: Optional[str] = None, public: Optional[bool] = None) -> None:
        """Update playlist details.
        
        Args:
            playlist_id: Spotify playlist ID
            name: New playlist name
            description: New playlist description
            public: New public status
        """
        kwargs = {}
        if name is not None:
            kwargs['name'] = name
        if description is not None:
            kwargs['description'] = description
        if public is not None:
            kwargs['public'] = public
        
        if kwargs:
            self.sp.playlist_change_details(playlist_id, **kwargs)