# yt-dlp

Installed: `2026.03.17` in `~/.venv` (via `uv pip install -U yt-dlp`).

## Basic usage

```
yt-dlp [OPTIONS] URL [URL...]
```

## Common recipes

```bash
# Download best quality video+audio, merged
yt-dlp URL

# Audio only, as MP3
yt-dlp -x --audio-format mp3 URL

# Best MP4 (single file, no merging)
yt-dlp -f "best[ext=mp4]" URL

# Specific resolution cap
yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" URL

# Entire playlist
yt-dlp URL                          # playlists auto-detected
yt-dlp --yes-playlist URL           # force playlist when ambiguous
yt-dlp --no-playlist URL            # single video from playlist URL

# Subtitles (embed + auto-generated)
yt-dlp --write-subs --write-auto-subs --sub-langs en --embed-subs URL

# Thumbnail + metadata embedded
yt-dlp --embed-thumbnail --embed-metadata URL

# Custom output filename
yt-dlp -o "%(uploader)s - %(title)s.%(ext)s" URL

# Download into specific directory
yt-dlp -P ~/Downloads/yt URL

# Resume / skip already-downloaded
yt-dlp --download-archive archive.txt URL
```

## Useful flags

| Flag | Purpose |
|---|---|
| `-f FORMAT` | Format selection (`best`, `bv+ba`, `bv*[height<=720]`) |
| `-F` | List all available formats for the URL |
| `-x` | Extract audio only |
| `--audio-format FMT` | `mp3`, `m4a`, `opus`, `wav`, ... |
| `--audio-quality 0` | Best audio quality (0=best, 10=worst) |
| `-o TEMPLATE` | Output filename template |
| `-P PATH` | Output directory |
| `-S SORT` | Sort formats (e.g. `-S "res:1080,codec:h264"`) |
| `--write-subs` / `--write-auto-subs` | Subtitle files |
| `--sub-langs L` | Languages (`en`, `en.*`, `all`) |
| `--embed-subs` / `--embed-thumbnail` / `--embed-metadata` | Mux into file |
| `--write-thumbnail` / `--write-info-json` | Save as sidecar files |
| `--download-archive FILE` | Skip URLs already logged |
| `-r RATE` | Rate limit (`500K`, `2M`) |
| `--cookies FILE` / `--cookies-from-browser B` | Auth (e.g. `--cookies-from-browser chrome`) |
| `-N N` | Parallel fragment downloads |
| `--playlist-items 1-3,7` | Select items from playlist |
| `--date YYYYMMDD` / `--dateafter` / `--datebefore` | Filter by upload date |
| `--match-filter EXPR` | Filter (`"duration<600 & !is_live"`) |
| `-q` / `-v` | Quiet / verbose |
| `--simulate` / `-s` | Don't download, just resolve |
| `-U` | Self-update (NB: managed by uv here — prefer `uv pip install -U yt-dlp`) |

## Output template fields

Common `%(...)s` fields: `title`, `uploader`, `upload_date`, `id`, `ext`, `resolution`, `fps`, `playlist_index`, `playlist_title`, `channel`, `duration_string`.

Example: `-o "%(upload_date>%Y-%m-%d)s - %(title).80s [%(id)s].%(ext)s"`

## Format syntax cheatsheet

- `best` — best pre-merged file
- `bv+ba` — best video + best audio, merged (needs ffmpeg)
- `bv*` — best video (may be muxed w/ audio)
- `bv[height<=720]+ba` — cap resolution
- `bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]` — prefer mp4 stack
- `worst` / `wv+wa` — smallest

## Dependencies

- **ffmpeg** required for merging, audio extraction, embedding. Install: `brew install ffmpeg`.

## See also

```
yt-dlp -h            # full option list (long!)
yt-dlp --help | less
```
