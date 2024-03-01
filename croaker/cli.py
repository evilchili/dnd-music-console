import io
import logging
import os
import sys
from pathlib import Path
from textwrap import dedent
from typing import List, Optional

import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

import croaker.path
from croaker import client, controller, server
from croaker.exceptions import ConfigurationError
from croaker.playlist import Playlist

SETUP_HELP = """
# Root directory for croaker configuration and logs. See also croaker --root.
CROAKER_ROOT=~/.dnd/croaker

## COMMAND AND CONTROL WEBSERVER

# Please make sure you set SECRET_KEY in your environment if you are running
# the command and control webserver. Clients do not need this.
SECRET_KEY=

# Where the record the webserver daemon's PID
PIDFILE=~/.dnd/croaker/croaker.pid

# Web interface configuration
HOST=127.0.0.1
PORT=8003

## CONTROLLER CLIENT

# The host and port to use when connecting to the websever.
CONTROLLER_HOST=127.0.0.1
CONTROLLER_PORT=8003

## MEDIA

# where to store playlist sources
PLAYLIST_ROOT=~/.dnd/croaker/playlists

# where to cache transcoded media files
CACHE_ROOT=~/.dnd/croaker/cache

# the kinds of files to add to playlists
MEDIA_GLOB=*.mp3,*.flac,*.m4a

# If defined, transcode media before streaming it, and cache it to disk. The
# strings INFILE and OUTFILE will be replaced with the media source file and
# the cached output location, respectively.
TRANSCODER=/usr/bin/ffmpeg -i INFILE '-hide_banner -loglevel error -codec:v copy -codec:a libmp3lame -q:a 2' OUTFILE

## LIQUIDSOAP AND ICECAST

# The liquidsoap executable
LIQUIDSOAP=/usr/bin/liquidsoap

# Icecast2 configuration for Liquidsoap
ICECAST_PASSWORD=
ICECAST_MOUNT=
ICECAST_HOST=
ICECAST_PORT=
ICECAST_URL=
"""


app = typer.Typer()
app_state = {}


@app.callback()
def main(
    context: typer.Context,
    root: Optional[Path] = typer.Option(
        Path("~/.dnd/croaker"),
        help="Path to the Croaker environment",
    ),
    host: Optional[str] = typer.Option(
        None,
        help="bind address",
    ),
    port: Optional[int] = typer.Option(
        None,
        help="bind port",
    ),
    debug: Optional[bool] = typer.Option(None, help="Enable debugging output"),
):
    load_dotenv(root.expanduser() / Path("defaults"))
    load_dotenv(stream=io.StringIO(SETUP_HELP))
    if host:
        os.environ["HOST"] = host
    if port:
        os.environ["PORT"] = port
    if debug is not None:
        if debug:
            os.environ["DEBUG"] = 1
        else:
            del os.environ["DEBUG"]

    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if debug else logging.INFO,
    )

    try:
        croaker.path.media_root()
        croaker.path.cache_root()
    except ConfigurationError as e:
        sys.stderr.write(f"{e}\n\n{SETUP_HELP}")
        sys.exit(1)

    app_state["client"] = client.Client(
        host=os.environ["CONTROLLER_HOST"],
        port=os.environ["CONTROLLER_PORT"],
    )

    if not context.invoked_subcommand:
        return play(context)


@app.command()
def setup(context: typer.Context):
    """
    (Re)Initialize Croaker.
    """
    sys.stderr.write("Interactive setup is not yet available. Sorry!\n")
    print(dedent(SETUP_HELP))


@app.command()
def start(
    context: typer.Context,
    daemonize: bool = typer.Option(True, help="Daemonize the webserver."),
):
    """
    Start the Croaker command and control webserver.
    """
    controller.start()
    if daemonize:
        server.daemonize()
    else:
        server.start()


@app.command()
def stop():
    """
    Terminate the webserver process and liquidsoap.
    """
    controller.stop()
    server.stop()


@app.command()
def play(
    playlist: str = typer.Argument(
        ...,
        help="Playlist name",
    )
):
    """
    Begin playing tracks from the directory $PLAYLIST_ROOT/[NAME].
    """
    res = app_state["client"].play(playlist)
    if res.status_code == 200:
        print("OK")


@app.command()
def skip():
    """
    Play the next track on the current playlist.
    """
    res = app_state["client"].skip()
    if res.status_code == 200:
        print("OK")


@app.command()
def add(
    playlist: str = typer.Argument(
        ...,
        help="Playlist name",
    ),
    theme: Optional[bool] = typer.Option(False, help="Make the first track the theme song."),
    tracks: Annotated[Optional[List[Path]], typer.Argument()] = None,
):
    """
    Recursively add one or more paths to the specified playlist. Tracks can be
    any combination of individual audio files and directories containing audio
    files; anything not already on the playlist will be added to it.

    If --theme is specified, the first track will be designated the playlist
    "theme." Theme songs get played first whenever the playlist is loaded,
    after which the playlist order is randomized.
    """
    pl = Playlist(name=playlist)
    pl.add(tracks, make_theme=theme)
    print(pl)


if __name__ == "__main__":
    app.main()
