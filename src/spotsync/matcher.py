"""Track matching module with fuzzy matching capabilities."""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from Levenshtein import ratio


@dataclass
class MatchResult:
    """Result of a track matching operation."""
    spotify_id: str
    confidence: float
    matched_title: str
    matched_artist: str
    original_title: str
    original_artist: Optional[str] = None


class TrackMatcher:
    """Handles fuzzy matching of tracks against Spotify search results."""
    
    def __init__(self, threshold: float = 0.8):
        """Initialize the matcher with a confidence threshold.
        
        Args:
            threshold: Minimum confidence score (0-1) for a match to be considered valid
        """
        self.threshold = threshold
    
    def match_track(self, local_title: str, local_artist: Optional[str], 
                   spotify_results: List[Dict]) -> Optional[MatchResult]:
        """Match a local track against Spotify search results.
        
        Args:
            local_title: Title from the M3U8 file
            local_artist: Artist from the M3U8 file (if available)
            spotify_results: List of track objects from Spotify API
            
        Returns:
            MatchResult if a good match is found, None otherwise
        """
        if not spotify_results:
            return None
        
        best_match = None
        best_score = 0.0
        
        # Clean the local track info
        clean_title = self._clean_string(local_title)
        clean_artist = self._clean_string(local_artist) if local_artist else ""
        
        for track in spotify_results:
            # Extract Spotify track info
            spotify_title = track.get('name', '')
            spotify_artists = [artist['name'] for artist in track.get('artists', [])]
            spotify_artist = ' '.join(spotify_artists)
            spotify_id = track.get('id')
            
            if not spotify_id:
                continue
            
            # Calculate match score
            score = self._calculate_match_score(
                clean_title, clean_artist,
                spotify_title, spotify_artist
            )
            
            if score > best_score:
                best_score = score
                best_match = MatchResult(
                    spotify_id=spotify_id,
                    confidence=score,
                    matched_title=spotify_title,
                    matched_artist=spotify_artist,
                    original_title=local_title,
                    original_artist=local_artist
                )
        
        # Return match only if it meets the threshold
        if best_match and best_match.confidence >= self.threshold:
            return best_match
        
        return None
    
    def _calculate_match_score(self, local_title: str, local_artist: str,
                              spotify_title: str, spotify_artist: str) -> float:
        """Calculate similarity score between local and Spotify tracks.
        
        Returns a score between 0 and 1, where 1 is a perfect match.
        """
        # Clean Spotify strings
        clean_spotify_title = self._clean_string(spotify_title)
        clean_spotify_artist = self._clean_string(spotify_artist)
        
        # Calculate title similarity
        title_score = ratio(local_title, clean_spotify_title)
        
        # If we have artist info, use it to improve matching
        if local_artist and clean_spotify_artist:
            artist_score = ratio(local_artist, clean_spotify_artist)
            
            # Check if local artist is contained in Spotify artists (for features)
            if local_artist.lower() in clean_spotify_artist.lower():
                artist_score = max(artist_score, 0.9)
            
            # Check if artists are the same but in different order
            local_words = set(local_artist.split())
            spotify_words = set(clean_spotify_artist.split())
            if local_words == spotify_words and len(local_words) > 1:
                artist_score = max(artist_score, 0.95)  # High score for same artists in different order
            
            # Weighted average: both title and artist are important
            # If artist score is very low, significantly penalize the overall score
            if artist_score < 0.6:
                total_score = (title_score * 0.4) + (artist_score * 0.6)  # Penalize bad artist matches
            else:
                total_score = (title_score * 0.6) + (artist_score * 0.4)  # Normal weighting
        else:
            # Only title available
            total_score = title_score
        
        # Bonus for exact matches (after cleaning)
        if local_title == clean_spotify_title:
            total_score = min(1.0, total_score + 0.1)
        
        return total_score
    
    def _clean_string(self, text: Optional[str]) -> str:
        """Clean and normalize a string for matching.
        
        - Converts to lowercase
        - Extracts and preserves important content from parentheses/brackets
        - Removes special characters
        - Normalizes whitespace
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Extract important content from parentheses and brackets before removing them
        # Look for remix information, features, etc.
        important_content = []
        
        # Extract remix info from brackets [...]
        bracket_matches = re.findall(r'\[([^\]]*(?:remix|mix|edit|version|rework)[^\]]*)\]', text)
        important_content.extend(bracket_matches)
        
        # Extract remix info from parentheses (...)  
        paren_matches = re.findall(r'\(([^)]*(?:remix|mix|edit|version|rework)[^)]*)\)', text)
        important_content.extend(paren_matches)
        
        # Extract featuring info but keep it simpler
        feat_matches = re.findall(r'\((?:feat\.?|featuring|ft\.?)\s*([^)]+)\)', text)
        # Only add featuring info if it's not already in the main text
        for feat in feat_matches:
            # Check if the featured artist is already mentioned in the text
            if not any(name.strip().lower() in text.lower() for name in feat.split('&') + feat.split(',') if name.strip()):
                important_content.append(feat)
        
        # Remove ALL content in parentheses and brackets now
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        
        # Add back the important content
        if important_content:
            text += ' ' + ' '.join(important_content)
        
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def find_best_matches(self, local_tracks: List[Tuple[str, Optional[str]]], 
                         spotify_results_list: List[List[Dict]]) -> List[Optional[MatchResult]]:
        """Match multiple local tracks against their respective Spotify search results.
        
        Args:
            local_tracks: List of (title, artist) tuples
            spotify_results_list: List of Spotify search results for each track
            
        Returns:
            List of MatchResult objects (or None for unmatched tracks)
        """
        if len(local_tracks) != len(spotify_results_list):
            raise ValueError("Number of local tracks must match number of result lists")
        
        matches = []
        for (title, artist), results in zip(local_tracks, spotify_results_list):
            match = self.match_track(title, artist, results)
            matches.append(match)
        
        return matches