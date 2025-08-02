"""M3U8 playlist parser module."""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Track:
    """Represents a track with metadata."""
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None
    file_path: Optional[str] = None


class M3U8Parser:
    """Parser for M3U8 playlist files."""
    
    def __init__(self):
        self.tracks: List[Track] = []
        self.playlist_name: Optional[str] = None
    
    def parse(self, file_path: str) -> List[Track]:
        """Parse an M3U8 playlist file and extract track information.
        
        Args:
            file_path: Path to the M3U8 file
            
        Returns:
            List of Track objects
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not a valid M3U8
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.suffix.lower() not in ['.m3u', '.m3u8']:
            raise ValueError(f"File must be .m3u or .m3u8, got: {path.suffix}")
        
        self.tracks.clear()
        self.playlist_name = path.stem
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if not lines or not lines[0].strip().startswith('#EXTM3U'):
            raise ValueError("Invalid M3U8 file: must start with #EXTM3U")
        
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('#EXTINF:'):
                # Parse extended info
                track = self._parse_extinf(line)
                
                # Next line should be the file path
                if i + 1 < len(lines):
                    file_line = lines[i + 1].strip()
                    if file_line and not file_line.startswith('#'):
                        track.file_path = file_line
                        self.tracks.append(track)
                        i += 2
                        continue
                
                i += 1
            elif line and not line.startswith('#'):
                # Plain file path without EXTINF
                track = self._parse_filename(line)
                track.file_path = line
                self.tracks.append(track)
                i += 1
            else:
                i += 1
        
        return self.tracks
    
    def _parse_extinf(self, line: str) -> Track:
        """Parse an EXTINF line to extract track info.
        
        Format: #EXTINF:duration,Artist - Title
        """
        # Remove #EXTINF: prefix
        info = line[8:].strip()
        
        # Split duration and track info
        parts = info.split(',', 1)
        duration = None
        track_info = info
        
        if len(parts) == 2:
            try:
                duration = int(float(parts[0]))
            except ValueError:
                pass
            track_info = parts[1].strip()
        
        # Try to parse "Artist - Title" format
        artist = None
        title = track_info
        
        if ' - ' in track_info:
            artist_title = track_info.split(' - ', 1)
            artist = artist_title[0].strip()
            title = artist_title[1].strip()
        
        return Track(title=title, artist=artist, duration=duration)
    
    def _parse_filename(self, filename: str) -> Track:
        """Extract track info from filename.
        
        Tries to parse common patterns like:
        - Artist - Title.mp3
        - 01. Artist - Title.mp3
        - Title.mp3
        """
        # Remove path and extension
        name = Path(filename).stem
        
        # Remove track numbers at the beginning
        name = re.sub(r'^\d+[\.\-\s]+', '', name)
        
        # Try to parse "Artist - Title" format
        artist = None
        title = name
        
        if ' - ' in name:
            parts = name.split(' - ', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        
        return Track(title=title, artist=artist)