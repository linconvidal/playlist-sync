"""Tests for M3U8 parser module."""

import pytest
from pathlib import Path
import tempfile

from spotsync.parser import M3U8Parser, Track


class TestM3U8Parser:
    """Test cases for M3U8Parser."""
    
    def test_parse_valid_m3u8_with_extinf(self):
        """Test parsing a valid M3U8 file with EXTINF tags."""
        content = """#EXTM3U
#EXTINF:180,Artist Name - Song Title
/path/to/song.mp3
#EXTINF:240,Another Artist - Another Song
/path/to/another.mp3
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m3u8', delete=False) as f:
            f.write(content)
            f.flush()
            
            parser = M3U8Parser()
            tracks = parser.parse(f.name)
            
            assert len(tracks) == 2
            
            assert tracks[0].title == "Song Title"
            assert tracks[0].artist == "Artist Name"
            assert tracks[0].duration == 180
            assert tracks[0].file_path == "/path/to/song.mp3"
            
            assert tracks[1].title == "Another Song"
            assert tracks[1].artist == "Another Artist"
            assert tracks[1].duration == 240
            
            Path(f.name).unlink()
    
    def test_parse_simple_m3u8(self):
        """Test parsing a simple M3U8 without EXTINF tags."""
        content = """#EXTM3U
/path/to/Artist - Song.mp3
/path/to/song2.mp3
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m3u8', delete=False) as f:
            f.write(content)
            f.flush()
            
            parser = M3U8Parser()
            tracks = parser.parse(f.name)
            
            assert len(tracks) == 2
            
            assert tracks[0].title == "Song"
            assert tracks[0].artist == "Artist"
            assert tracks[0].file_path == "/path/to/Artist - Song.mp3"
            
            assert tracks[1].title == "song2"
            assert tracks[1].artist is None
            
            Path(f.name).unlink()
    
    def test_parse_invalid_file(self):
        """Test parsing an invalid M3U8 file."""
        content = """Not a valid M3U8 file"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m3u8', delete=False) as f:
            f.write(content)
            f.flush()
            
            parser = M3U8Parser()
            with pytest.raises(ValueError, match="Invalid M3U8 file"):
                parser.parse(f.name)
            
            Path(f.name).unlink()
    
    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file."""
        parser = M3U8Parser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/file.m3u8")
    
    def test_parse_wrong_extension(self):
        """Test parsing a file with wrong extension."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("#EXTM3U\n")
            f.flush()
            
            parser = M3U8Parser()
            with pytest.raises(ValueError, match="File must be .m3u or .m3u8"):
                parser.parse(f.name)
            
            Path(f.name).unlink()
    
    def test_parse_extinf_formats(self):
        """Test parsing various EXTINF formats."""
        parser = M3U8Parser()
        
        # Test with integer duration
        track = parser._parse_extinf("#EXTINF:123,Artist - Title")
        assert track.duration == 123
        assert track.artist == "Artist"
        assert track.title == "Title"
        
        # Test with float duration
        track = parser._parse_extinf("#EXTINF:123.45,Artist - Title")
        assert track.duration == 123
        
        # Test without artist
        track = parser._parse_extinf("#EXTINF:60,Just a Title")
        assert track.duration == 60
        assert track.artist is None
        assert track.title == "Just a Title"
        
        # Test with malformed duration
        track = parser._parse_extinf("#EXTINF:abc,Title")
        assert track.duration is None
        assert track.title == "Title"
    
    def test_parse_filename(self):
        """Test filename parsing."""
        parser = M3U8Parser()
        
        # Test "Artist - Title.mp3" format
        track = parser._parse_filename("/path/to/Artist Name - Song Title.mp3")
        assert track.artist == "Artist Name"
        assert track.title == "Song Title"
        
        # Test with track number
        track = parser._parse_filename("01. Artist - Title.mp3")
        assert track.artist == "Artist"
        assert track.title == "Title"
        
        # Test without artist
        track = parser._parse_filename("Just a Title.mp3")
        assert track.artist is None
        assert track.title == "Just a Title"