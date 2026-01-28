import requests
import argparse
import sys
import os
from mutagen import File
from pathlib import Path
import time

BASE_URL = "https://apic.musixmatch.com/ws/1.1/"


def main():
    parser = argparse.ArgumentParser(description="MxD, a Musixmatch utility, version 1.0, by ElliotCHEN37")

    parser.add_argument("path", nargs="?", default=None, help="Path to audio file or folder")
    parser.add_argument("-a", "--artist", help="Artist Name")
    parser.add_argument("-t", "--track", help="Track Title")
    parser.add_argument("--token", help="User Token (optional)")
    parser.add_argument("--synced", action="store_true", help="Download synced lyric (optional)")
    parser.add_argument("--max-depth", type=int, default=1, help="Max searching depth in sub-folder")
    parser.add_argument("--wait", type=float, default=30.0, help="Wait for a moment between downloads")

    args = parser.parse_args()


    if args.token:
        print("User token available, continue")
        token = args.token
    else:
        print("User token not available, requesting")
        token = IfTokenAvailable()

    if args.path:
        path_obj = Path(args.path)
        if path_obj.exists():
            print(f"Processing: {args.path}")
            files = scan(args.path, args.max_depth)

            for file_path in files:
                artist, track = processMetaData(file_path)
                if not artist or not track:
                    print(f"Skipping: {file_path.name}")
                    continue

                save_dest = file_path.with_suffix(".lrc")

                lyric_data = fetchLyric(artist, track, token)
                parseLyric(lyric_data, save_dest, args.synced)

                print(f"Waiting for {args.wait} seconds")
                time.sleep(args.wait)

        else:
            print(f"Error: Path '{args.path}' does not exist.")

    elif args.artist and args.track:
        print(f"Manual: {args.artist} - {args.track}")
        save_dest = f"{args.artist} - {args.track}.lrc"

        lyric_data = fetchLyric(args.artist, args.track, token)
        parseLyric(lyric_data, save_dest, args.synced)

    else:
        print("Error: Please provide a path or both artist (-a) and track (-t).")

def requestToken():
    print("Requesting token")
    token_response = requests.get(BASE_URL + "token.get?app_id=web-desktop-app-v1.0")
    print("Parsing token")
    token_data = token_response.json()
    token = token_data["message"]["body"]["user_token"]
    print("Parsed successful")
    return token

def fetchLyric(ARTIST, TRACK, token):
    print("Requesting lyric")
    params = {
        "format": "json",
        "namespace": "lyrics_richsynched",
        "subtitle_format": "lrc",
        "app_id": "web-desktop-app-v1.0",
        "q_artist": ARTIST,
        "q_track": TRACK,
        "usertoken": token
    }

    lyric_response = requests.get(BASE_URL + "macro.subtitles.get", params=params)
    lyric_data = lyric_response.json()
    return lyric_data

def parseLyric(lyric_data, destination, use_synced):
    print("Parsing lyric")
    requestStatusCode = lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["header"]["status_code"]

    if requestStatusCode == 200:
        print("Status code == 200")
        lyricIfRestricted = lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["body"]["lyrics"]["restricted"]
        lyricIfInstrumental = lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["body"]["lyrics"]["instrumental"]
        lyricBody = lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["body"]["lyrics"]["lyrics_body"]
        lyricIfSyncedAvailable = lyric_data["message"]["body"]["macro_calls"]["track.subtitles.get"]["message"]["header"]["available"]

        if lyricIfRestricted:
            print("Restricted lyric")
            sys.exit(0)
        elif lyricIfInstrumental:
            print("Instrumental")
            writeFile(destination, f"This song is instrumental.\nLet the music play...")
        elif lyricIfSyncedAvailable:
            if use_synced:
                print("Synced lyric available, writing")
                lyricSyncedBody = lyric_data["message"]["body"]["macro_calls"]["track.subtitles.get"]["message"]["body"]["subtitle_list"][0]["subtitle"]["subtitle_body"]
                writeFile(destination, lyricSyncedBody)
            else:
                print("Writing the unsynced one")
                writeFile(destination, lyricBody)
        else:
            print("Synced lyric not available, using the unsynced one instead")
            writeFile(destination, lyricBody)

    else:
        print(f"Error occurred, status code: {requestStatusCode}")

def writeFile(destination, content):
    print("Writing file")
    with open(destination, "w", encoding="utf-8") as f:
        f.write(content)
    print("Done")

def IfTokenAvailable():
    if os.path.exists("./.token"):
        print("Saved token found")
        with open("./.token", "r") as f:
            print("Token read")
            return f.read().strip()
    else:
        print("No saved token found, requesting")
        token = requestToken()
        writeFile(".token", token)
        print("Token written")
        return token

def processMetaData(file_path):
    audio = File(file_path)
    if audio is None:
        return None, None

    artist_keys = ['artist', 'TPE1', '\xa9ART', 'aART']
    track_keys = ['title', 'TIT2', '\xa9nam']

    artist = None
    for key in artist_keys:
        if key in audio:
            artist = str(audio[key][0])
            for separator in ['/', ',', ';', '&', 'feat.', 'with']:
                if separator in artist.lower():
                    artist = artist.split(separator, 1)[0].strip()
            break

    track = None
    for key in track_keys:
        if key in audio:
            track = str(audio[key][0])
            break

    print(f"Read Artist: {artist}, Track: {track}")
    return artist, track

def scan(path, max_depth, current_depth=1):
    print("Scanning directory")
    format_list = {'.mp3', '.flac', '.m4a', '.ogg', '.wav'}

    if os.path.isfile(path):
        if os.path.splitext(path)[1].lower() in format_list:
            return [Path(path)]
        else:
            return []

    found_files = []

    try:
        entries = list(os.scandir(path))
    except PermissionError:
        return []

    for entry in entries:
        if entry.is_file() and os.path.splitext(entry.name)[1].lower() in format_list:
            found_files.append(Path(entry.path))

        elif entry.is_dir():
            if max_depth == 0 or current_depth < max_depth:
                found_files.extend(scan(entry.path, max_depth, current_depth + 1))

    return found_files

if __name__ == "__main__":
    main()
