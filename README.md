# Spotify Playlist Downloader

A Python script that downloads tracks from Spotify playlists (including your liked songs and top tracks) as high-quality MP3 files with metadata and album art.

## Features

- Download entire Spotify playlists (public or private)
- Download your liked songs
- Download your top tracks
- Get and download recommended tracks
- Preserves all metadata (artist, album, track number, etc.)
- Embeds album artwork
- Configurable audio quality (190kbps or 320kbps)
- Organized folder structure (Artist/Album/Track.mp3)

## Prerequisites

- Python 3.6+
- FFmpeg
- Spotify Developer Account
- YouTube access (for audio source)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/iaceene/spotify-downloader.git
   cd spotify-downloader
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Spotify API credentials**:
   - Create an app at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Set environment variables:
     ```bash
     export SPOTIFY_CLIENT_ID='your_client_id'
     export SPOTIFY_CLIENT_SECRET='your_client_secret'
     ```

4. **Install FFmpeg**:
   - Linux: `sudo apt install ffmpeg`
   - Mac: `brew install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Usage

Run the script:
```bash
python spotify_downloader.py
```

### Menu Options:
1. **Download a playlist** - Choose from your Spotify playlists
2. **Download liked songs** - Downloads all your saved tracks
3. **Download top tracks** - Your most played tracks
4. **Recommendations based on playlist** - Discover new music
5. **Recommendations based on top tracks** - More personalized suggestions
6. **Set audio quality** - Choose between 190kbps or 320kbps
7. **Change download directory** - Default: `~/.spotify_downloader/downloads/`
8. **Exit**

Files are saved in: `[download_directory]/[Playlist Name]/[Artist]/[Album]/[Artist] - [Track].mp3`

## Configuration

The script creates a configuration directory at `~/.spotify_downloader/` containing:
- `user_token.txt` - Spotify authentication token
- `downloads/` - Default download location

To change defaults, modify these environment variables:
```bash
export SPOTIFY_DOWNLOAD_DIR="/path/to/new/location"
export SPOTIFY_DEFAULT_QUALITY="190"  # or "320"
```

## Legal Notice

This project is for **educational purposes only**. Downloading copyrighted material may violate Spotify's Terms of Service. Please only download music you have rights to.

## Troubleshooting

**Authentication issues:**
- Delete `~/.spotify_downloader/user_token.txt` and restart
- Ensure your Spotify app has the correct redirect URI (`http://localhost:5000/callback`)

**Download failures:**
- Check your internet connection
- Verify FFmpeg is installed and in your PATH
- Update yt-dlp: `pip install --upgrade yt-dlp`

**Metadata issues:**
- Install the latest eyed3: `pip install --upgrade eyed3`

## Contributing

Pull requests are welcome! For major changes, please open an issue first.
