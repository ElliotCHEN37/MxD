# MxD

----
MxD can help you fetch lyrics from Musixmatch<br>

----
### Usage

1. Install requirements<br>
`pip install -r requirements.txt`
2. Run with Python<br>
`python main.py -h`
3. Here's the output<br>
```commandline
usage: main.py [-h] [-a ARTIST] [-t TRACK] [-l ALBUM] [--token TOKEN] [--refresh-token] [--synced] [--overwrite] [--max-depth MAX_DEPTH] [--wait WAIT] [path]

MxD, a Musixmatch utility, version 1.1(3), by ElliotCHEN37

positional arguments:
  path                  Path to audio file or folder

optional arguments:
  -h, --help            show this help message and exit
  -a ARTIST, --artist ARTIST
                        Artist Name
  -t TRACK, --track TRACK
                        Track Title
  -l ALBUM, --album ALBUM
                        Album Name
  --token TOKEN         User Token (optional)
  --refresh-token       Refresh user token
  --synced              Download synced lyric (optional)
  --overwrite           Overwrite existing .lrc files
  --max-depth MAX_DEPTH
                        Max searching depth in sub-folder
  --wait WAIT           Wait for a moment between downloads
```

----
### Thanks

- [EeveeSpotify](https://github.com/whoeevee/EeveeSpotify) for Musixmatch request API
- [Lyrics Plus from Spicetify](https://github.com/spicetify/cli) for Musixmatch user token API
