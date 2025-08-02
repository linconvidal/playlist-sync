"""Tests for track matcher module."""

import pytest
from spotsync.matcher import TrackMatcher, MatchResult


class TestTrackMatcher:
    """Test cases for TrackMatcher."""
    
    @pytest.fixture
    def matcher(self):
        """Create a TrackMatcher instance."""
        return TrackMatcher(threshold=0.8)
    
    @pytest.fixture
    def spotify_results(self):
        """Sample Spotify search results."""
        return [
            {
                'id': 'track1',
                'name': 'Bohemian Rhapsody',
                'artists': [{'name': 'Queen'}]
            },
            {
                'id': 'track2',
                'name': 'Bohemian Rhapsody (Remastered)',
                'artists': [{'name': 'Queen'}]
            },
            {
                'id': 'track3',
                'name': 'Another Song',
                'artists': [{'name': 'Different Artist'}]
            }
        ]
    
    def test_exact_match(self, matcher, spotify_results):
        """Test exact title and artist match."""
        result = matcher.match_track('Bohemian Rhapsody', 'Queen', spotify_results)
        
        assert result is not None
        assert result.spotify_id == 'track1'
        assert result.confidence > 0.9
        assert result.matched_title == 'Bohemian Rhapsody'
        assert result.matched_artist == 'Queen'
    
    def test_fuzzy_match(self, matcher, spotify_results):
        """Test fuzzy matching with slight differences."""
        result = matcher.match_track('Bohemian Rhapsody', 'queen', spotify_results)
        
        assert result is not None
        assert result.spotify_id in ['track1', 'track2']
        assert result.confidence > 0.8
    
    def test_no_match_below_threshold(self, matcher, spotify_results):
        """Test that no match is returned when confidence is below threshold."""
        result = matcher.match_track('Completely Different Song', 'Unknown Artist', spotify_results)
        
        assert result is None
    
    def test_match_without_artist(self, matcher, spotify_results):
        """Test matching with only title."""
        result = matcher.match_track('Bohemian Rhapsody', None, spotify_results)
        
        assert result is not None
        assert result.spotify_id in ['track1', 'track2']
        assert result.confidence > 0.7
    
    def test_empty_results(self, matcher):
        """Test with empty Spotify results."""
        result = matcher.match_track('Any Song', 'Any Artist', [])
        
        assert result is None
    
    def test_clean_string(self, matcher):
        """Test string cleaning functionality."""
        assert matcher._clean_string('Song (feat. Artist)') == 'song'
        assert matcher._clean_string('Song [Remix]') == 'song remix'  # Remix info is preserved
        assert matcher._clean_string('Song!!!') == 'song'
        assert matcher._clean_string('  Multiple   Spaces  ') == 'multiple spaces'
        assert matcher._clean_string(None) == ''
    
    def test_calculate_match_score(self, matcher):
        """Test match score calculation."""
        # Exact match
        score = matcher._calculate_match_score('song', 'artist', 'Song', 'Artist')
        assert score > 0.9
        
        # Close match
        score = matcher._calculate_match_score('bohemian rhapsody', 'queen', 
                                             'Bohemian Rhapsody', 'Queen')
        assert score == 1.0
        
        # Partial match
        score = matcher._calculate_match_score('song', 'artist', 
                                             'Different Song', 'Artist')
        assert 0.3 < score < 0.7
    
    def test_find_best_matches(self, matcher):
        """Test matching multiple tracks."""
        local_tracks = [
            ('Bohemian Rhapsody', 'Queen'),
            ('Unknown Song', None)
        ]
        
        spotify_results_list = [
            [
                {
                    'id': 'track1',
                    'name': 'Bohemian Rhapsody',
                    'artists': [{'name': 'Queen'}]
                }
            ],
            []  # No results for second track
        ]
        
        matches = matcher.find_best_matches(local_tracks, spotify_results_list)
        
        assert len(matches) == 2
        assert matches[0] is not None
        assert matches[0].spotify_id == 'track1'
        assert matches[1] is None
    
    def test_featuring_artist_match(self, matcher):
        """Test matching when local artist is featured in Spotify result."""
        spotify_results = [
            {
                'id': 'track1',
                'name': 'Song Title',
                'artists': [{'name': 'Main Artist'}, {'name': 'Featured Artist'}]
            }
        ]
        
        result = matcher.match_track('Song Title', 'Featured Artist', spotify_results)
        
        assert result is not None
        assert result.confidence > 0.8

    def test_artist_order_different(self, matcher):
        """Test matching when artists are in different order."""
        local_title = 'Risk'
        local_artist = 'Bas / FKJ'
        
        spotify_results = [{
            'id': '5TOc3JrAmrru8EDwoUXlaf',
            'name': 'Risk',
            'artists': [
                {'name': 'FKJ'},
                {'name': 'Bas'}
            ]
        }]
        
        result = matcher.match_track(local_title, local_artist, spotify_results)
        
        assert result is not None
        assert result.spotify_id == '5TOc3JrAmrru8EDwoUXlaf'
        assert result.confidence >= 0.83  # Should meet threshold despite different order