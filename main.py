import tekore as tk
import os
import yt_dlp as youtube_dl
import eyed3
import urllib.request
import urllib.parse
import re
from typing import List, Optional, Tuple

# Configuration
CONFIG_DIR = os.path.expanduser('~/.spotify_downloader')
TOKEN_FILE = os.path.join(CONFIG_DIR, 'user_token.txt')
DEFAULT_DOWNLOAD_DIR = os.path.join(CONFIG_DIR, 'downloads')

# Ensure config directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)

# Spotify API - THESE SHOULD BE SET AS ENVIRONMENT VARIABLES IN PRODUCTION
# Get these from your Spotify Developer Dashboard
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', 'YOUR_CLIENT_ID_HERE')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', 'YOUR_CLIENT_SECRET_HERE')
REDIRECT_URI = 'http://localhost:5000/callback'

# Initialize Spotify client
def initialize_spotify_client() -> tk.Spotify:
    """Initialize and return an authenticated Spotify client."""
    user_token = None
    
    # Try to load token from file
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                user_token = f.read().strip()
        except IOError as e:
            print(f"Warning: Could not read token file: {e}")

    # Validate or refresh token
    if user_token:
        try:
            spotify = tk.Spotify(user_token)
            spotify.current_user()  # Test the token
            return spotify
        except (tk.HTTPError, tk.Unauthorised):
            print("Existing token is invalid, requesting new one...")

    # Get new token if none exists or existing one is invalid
    user_token = tk.prompt_for_user_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=tk.scope.every
    )
    
    # Save the new token
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(str(user_token))
    except IOError as e:
        print(f"Warning: Could not save token: {e}")

    return tk.Spotify(user_token)

spotify = initialize_spotify_client()

class DownloadLogger:
    """Logger for yt-dlp to handle output messages."""
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(f"Download error: {msg}")

def sanitize_filename(filename: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    # Replace spaces and trim
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename[:255]  # Limit length to prevent filesystem issues

def get_yt_dlp_options(quality: str = '320', output_template: str = None) -> dict:
    """Return configuration options for yt-dlp."""
    ffmpeg_location = os.getenv('FFMPEG_PATH', 'ffmpeg')  # Default to assuming ffmpeg is in PATH
    
    opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': output_template or '%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }],
        'logger': DownloadLogger(),
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': ffmpeg_location,
        'addmetadata': True,
        'embedthumbnail': True,
    }
    return opts

def download_track(track: tk.model.FullTrack, download_dir: str, quality: str) -> bool:
    """Download a single track and return success status."""
    artist = sanitize_filename(track.artists[0].name)
    song = sanitize_filename(track.name)
    album = sanitize_filename(track.album.name)
    
    # Create directory structure: download_dir/Artist/Album/
    album_dir = os.path.join(download_dir, artist, album)
    os.makedirs(album_dir, exist_ok=True)
    
    # Final file path
    filename = f"{artist} - {song}.mp3"
    filepath = os.path.join(album_dir, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"Already exists: {filename}")
        return True
    
    print(f"Downloading: {filename}")
    
    # Search query for YouTube
    query = f"{artist} {song} official audio"
    ydl_opts = get_yt_dlp_options(
        quality=quality,
        output_template=os.path.join(album_dir, f"{artist} - {song}.%(ext)s")
    )
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            # Search and download
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            if not info or not info.get('entries'):
                print(f"No results found for: {query}")
                return False
            
            # Verify download
            if not os.path.exists(filepath):
                print(f"Download failed: {filename}")
                return False
            
            # Add metadata
            try:
                audiofile = eyed3.load(filepath)
                if audiofile.tag is None:
                    audiofile.initTag()
                
                audiofile.tag.artist = artist
                audiofile.tag.title = song
                audiofile.tag.album = album
                audiofile.tag.album_artist = track.album.artists[0].name
                audiofile.tag.track_num = track.track_number
                
                # Add genre if available
                if track.artists[0].id:
                    artist_info = spotify.artist(track.artists[0].id)
                    if artist_info.genres:
                        audiofile.tag.genre = artist_info.genres[0]
                
                # Add album art
                if track.album.images:
                    image_url = track.album.images[0].url
                    with urllib.request.urlopen(image_url) as response:
                        imagedata = response.read()
                    audiofile.tag.images.set(3, imagedata, 'image/jpeg')
                
                audiofile.tag.save()
            except Exception as e:
                print(f"Failed to add metadata to {filename}: {e}")
            
            return True
            
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        # Clean up partially downloaded files
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        return False

def download_tracks(tracks: List[tk.model.FullTrack], playlist_name: str, quality: str = '320'):
    """Download multiple tracks to a playlist directory."""
    download_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, sanitize_filename(playlist_name))
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\nDownloading {len(tracks)} tracks to: {download_dir}")
    
    success_count = 0
    for i, track in enumerate(tracks, 1):
        print(f"\nTrack {i}/{len(tracks)}:")
        if download_track(track, download_dir, quality):
            success_count += 1
    
    print(f"\nDownload complete. Successfully downloaded {success_count}/{len(tracks)} tracks.")

def get_playlist_tracks(playlist_id: str) -> List[tk.model.FullTrack]:
    """Get all tracks from a playlist."""
    tracks = []
    results = spotify.playlist_items(playlist_id)
    tracks.extend([item.track for item in results.items if item.track])
    
    while results.next:
        results = spotify.next(results)
        tracks.extend([item.track for item in results.items if item.track])
    
    return tracks

def get_user_playlists() -> List[tk.model.SimplePlaylist]:
    """Get all playlists for the current user."""
    playlists = []
    results = spotify.playlists(spotify.current_user().id)
    playlists.extend(results.items)
    
    while results.next:
        results = spotify.next(results)
        playlists.extend(results.items)
    
    return playlists

def list_user_playlists():
    """List all user playlists with numbering."""
    playlists = get_user_playlists()
    for i, playlist in enumerate(playlists, 1):
        print(f"{i}. {playlist.name} ({playlist.tracks.total} tracks)")
    return playlists

def get_liked_songs() -> List[tk.model.FullTrack]:
    """Get all liked songs for the current user."""
    tracks = []
    results = spotify.saved_tracks()
    tracks.extend([item.track for item in results.items])
    
    while results.next:
        results = spotify.next(results)
        tracks.extend([item.track for item in results.items])
    
    return tracks

def get_top_tracks(limit: int = 20) -> List[tk.model.FullTrack]:
    """Get user's top tracks."""
    return spotify.current_user_top_tracks(limit=limit).items

def get_recommendations(tracks: List[tk.model.FullTrack], limit: int = 20) -> List[tk.model.FullTrack]:
    """Get recommendations based on given tracks."""
    seed_tracks = [t.id for t in tracks[:5]]  # Use first 5 tracks as seeds
    return spotify.recommendations(seed_tracks=seed_tracks, limit=limit).tracks

def display_menu():
    """Display the main menu."""
    print("\nSpotify Downloader Menu:")
    print("1. Download a playlist")
    print("2. Download liked songs")
    print("3. Download top tracks")
    print("4. Download recommendations based on a playlist")
    print("5. Download recommendations based on top tracks")
    print("6. Set download quality (current: 320 kbps)")
    print("7. Change download directory (current: {DEFAULT_DOWNLOAD_DIR})")
    print("8. Exit")
    return input("Enter your choice: ")

def main():
    current_quality = '320'
    
    print(f"Logged in as: {spotify.current_user().display_name}")
    print(f"Download directory: {DEFAULT_DOWNLOAD_DIR}")
    
    while True:
        choice = display_menu()
        
        if choice == '1':  # Download playlist
            playlists = list_user_playlists()
            if not playlists:
                print("No playlists found.")
                continue
                
            try:
                selection = int(input("Select playlist number: ")) - 1
                if 0 <= selection < len(playlists):
                    playlist = playlists[selection]
                    tracks = get_playlist_tracks(playlist.id)
                    download_tracks(tracks, playlist.name, current_quality)
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '2':  # Download liked songs
            print("Getting liked songs...")
            tracks = get_liked_songs()
            download_tracks(tracks, "Liked Songs", current_quality)
            
        elif choice == '3':  # Download top tracks
            try:
                limit = int(input("How many top tracks? (1-50): "))
                limit = max(1, min(50, limit))
                tracks = get_top_tracks(limit)
                download_tracks(tracks, "Top Tracks", current_quality)
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '4':  # Recommendations from playlist
            playlists = list_user_playlists()
            if not playlists:
                print("No playlists found.")
                continue
                
            try:
                selection = int(input("Select playlist number: ")) - 1
                if 0 <= selection < len(playlists):
                    playlist = playlists[selection]
                    tracks = get_playlist_tracks(playlist.id)
                    recommendations = get_recommendations(tracks)
                    download_tracks(recommendations, f"Recommendations for {playlist.name}", current_quality)
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '5':  # Recommendations from top tracks
            try:
                limit = int(input("How many top tracks to base recommendations on? (1-5): "))
                limit = max(1, min(5, limit))
                tracks = get_top_tracks(limit)
                recommendations = get_recommendations(tracks)
                download_tracks(recommendations, "Recommendations from Top Tracks", current_quality)
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '6':  # Set quality
            quality = input("Enter quality (190 or 320): ")
            if quality in ('190', '320'):
                current_quality = quality
                print(f"Quality set to {quality} kbps")
            else:
                print("Invalid quality. Must be 190 or 320.")
                
        elif choice == '7':  # Change download directory
            global DEFAULT_DOWNLOAD_DIR
            new_dir = input(f"Enter new download directory (current: {DEFAULT_DOWNLOAD_DIR}): ")
            if new_dir.strip():
                DEFAULT_DOWNLOAD_DIR = os.path.expanduser(new_dir.strip())
                os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)
                print(f"Download directory changed to {DEFAULT_DOWNLOAD_DIR}")
                
        elif choice == '8':  # Exit
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
