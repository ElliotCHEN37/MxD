import requests
import argparse
import os
from mutagen import File
from pathlib import Path
import time
import logging

BASE_URL = "https://apic.musixmatch.com/ws/1.1/"


def main():
    parser = argparse.ArgumentParser(description="MxD, a Musixmatch utility, version 1.2(2), by ElliotCHEN37")

    parser.add_argument("path", nargs="?", default=None, help="Path to audio file or folder")
    parser.add_argument("-a", "--artist", help="Artist Name")
    parser.add_argument("-t", "--track", help="Track Title")
    parser.add_argument("-l", "--album", help="Album Name")
    parser.add_argument("--token", help="User Token (optional)")
    parser.add_argument("--refresh-token", action="store_true", help="Refresh user token")
    parser.add_argument("--synced", action="store_true", help="Download synced lyric (optional)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .lrc files")
    parser.add_argument("--max-depth", type=int, default=1, help="Max searching depth in sub-folder")
    parser.add_argument("--wait", type=float, default=30.0, help="Wait for a moment between downloads")
    parser.add_argument("-v", "--verbose", action="store_true", help="Display detailed debug information")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler("log.txt", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    if args.token:
        logging.info("User token available, continue")
        token = args.token
    elif args.refresh_token:
        logging.info("Refreshing user token")
        token = requestToken()
        writeFile(".token", token)
        logging.debug("Token written")
    else:
        logging.debug("User token not provided")
        token = IfTokenAvailable()

    if args.path:
        ifRaisedRequest = False
        path_obj = Path(args.path)
        if path_obj.exists():
            logging.debug(f"Processing: {args.path}")
            files = scan(args.path, args.max_depth)

            for i, file_path in enumerate(files):
                artist, track, album = processMetaData(file_path)
                if not artist or not track:
                    logging.warning(f"Skipping: {file_path.name}")
                    continue

                save_dest = file_path.with_suffix(".lrc")

                if save_dest.exists() and not args.overwrite:
                    logging.warning(f"Skipping: {artist} - {track}")
                    continue

                if ifRaisedRequest:
                    logging.info(f"Waiting for {args.wait} seconds")
                    time.sleep(args.wait)

                lyric_data = fetchLyric(artist, track, token, album)
                ifRaisedRequest = True
                parseLyric(lyric_data, save_dest, args.synced)

        else:
            logging.error(f"Error: Path '{args.path}' does not exist.")

    elif args.artist and args.track:
        logging.debug(f"Manual: {args.artist} - {args.track}")
        save_dest = f"{args.artist} - {args.track}.lrc"

        lyric_data = fetchLyric(args.artist, args.track, token)
        parseLyric(lyric_data, save_dest, args.synced)

    else:
        logging.error("Error: Please provide a path or both artist (-a) and track (-t).")


def requestToken():
    logging.debug("Requesting token")
    token_response = requests.get(BASE_URL + "token.get?app_id=web-desktop-app-v1.0", timeout=10)
    logging.debug("Parsing token")
    token_data = token_response.json()
    token = token_data["message"]["body"]["user_token"]
    logging.info("Parsed successful, writing")
    return token


def fetchLyric(ARTIST, TRACK, token, ALBUM=None):
    logging.info("Requesting lyric")
    params = {
        "format": "json",
        "namespace": "lyrics_richsynched",
        "subtitle_format": "lrc",
        "app_id": "web-desktop-app-v1.0",
        "q_artist": ARTIST,
        "q_track": TRACK,
        "usertoken": token
    }

    if ALBUM:
        params["q_album"] = ALBUM

    lyric_response = requests.get(BASE_URL + "macro.subtitles.get", params=params, timeout=10)
    lyric_data = lyric_response.json()
    return lyric_data


def parseLyric(lyric_data, destination, use_synced):
    logging.info("Parsing lyric")
    try:
        requestStatusCode = lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["header"][
            "status_code"]

        if requestStatusCode == 401:
            logging.error("Token invalid")

        elif requestStatusCode == 200:
            logging.debug("Status code == 200")
            lyricIfRestricted = \
                lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["body"]["lyrics"][
                    "restricted"]
            lyricIfInstrumental = \
                lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["body"]["lyrics"][
                    "instrumental"]
            lyricBody = lyric_data["message"]["body"]["macro_calls"]["track.lyrics.get"]["message"]["body"]["lyrics"][
                "lyrics_body"]
            lyricIfSyncedAvailable = \
                lyric_data["message"]["body"]["macro_calls"]["track.subtitles.get"]["message"]["header"]["available"]

            if lyricIfRestricted:
                logging.error("Restricted lyric")
                return
            elif lyricIfInstrumental:
                logging.info("Instrumental")
                writeFile(destination, f"This song is instrumental.\nLet the music play...")
            elif lyricIfSyncedAvailable:
                if use_synced:
                    logging.debug("Synced lyric available, writing")
                    lyricSyncedBody = \
                        lyric_data["message"]["body"]["macro_calls"]["track.subtitles.get"]["message"]["body"][
                            "subtitle_list"][0]["subtitle"]["subtitle_body"]
                    writeFile(destination, lyricSyncedBody)
                else:
                    logging.info("Writing the unsynced one")
                    writeFile(destination, lyricBody)
            else:
                logging.warning("Synced lyric not available, using the unsynced one instead")
                writeFile(destination, lyricBody)

        else:
            logging.error(f"Error occurred, status code: {requestStatusCode}")
    except (KeyError, TypeError) as e:
        logging.error(f"Error occurred when parsing response: {e}", exc_info=True)
        return


def writeFile(destination, content):
    logging.debug(f"Attempting to write to {destination}")
    try:
        with open(destination, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"Successfully written: {destination}")
    except OSError as e:
        logging.error(f"File system error occurred when writing to {destination}: {e}")
    except Exception as e:
        logging.error(f"Error occurred when writing to {destination}: {e}", exc_info=True)


def IfTokenAvailable():
    if os.path.exists("./.token"):
        logging.debug("Saved token found")
        with open("./.token", "r") as f:
            logging.debug("Token read")
            return f.read().strip()
    else:
        logging.info("No saved token found, requesting")
        token = requestToken()
        writeFile(".token", token)
        logging.debug("Token written")
        return token


def processMetaData(file_path):
    audio = File(file_path)
    if audio is None:
        return None, None

    artist_keys = ['artist', 'TPE1', '\xa9ART', 'aART']
    track_keys = ['title', 'TIT2', '\xa9nam']
    album_keys = ['album', 'TALB', '\xa9alb']

    artist = None
    for key in artist_keys:
        if key in audio:
            artist = str(audio[key][0])
            for separator in ['/', ',', ';', '&', 'feat. ', 'with ']:
                if separator in artist.lower():
                    artist = artist.split(separator, 1)[0].strip()
            break

    track = None
    for key in track_keys:
        if key in audio:
            track = str(audio[key][0])
            break

    album = None
    for key in album_keys:
        if key in audio:
            album = str(audio[key][0])
            break

    logging.debug(f"Read Artist: {artist}, Track: {track}, Album: {album}")
    return artist, track, album


def scan(path, max_depth):
    path_obj = Path(path)
    format_list = ['*.mp3', '*.flac', '*.m4a', '*.ogg', '*.wav']
    found_files = []

    if path_obj.is_file():
        if any(path_obj.match(ext) for ext in format_list):
            found_files.append(path_obj)
        return found_files

    if path_obj.is_dir():
        if max_depth == 0:
            for ext in format_list:
                found_files.extend(path_obj.rglob(ext))
        else:
            for d in range(1, max_depth + 1):
                depth_prefix = "/".join(["*"] * (d - 1))
                if depth_prefix:
                    depth_prefix += "/"

                for ext in format_list:
                    pattern = depth_prefix + ext
                    found_files.extend(path_obj.glob(pattern))

    return found_files


if __name__ == "__main__":
    main()
