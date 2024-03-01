import logging
import os
from pathlib import Path
from subprocess import Popen
from time import sleep

from Exscript.protocols import Telnet

from croaker import path
from croaker.pidfile import pidfile
from croaker.playlist import Playlist, load_playlist

NOW_PLAYING = None

LIQUIDSOAP_CONFIG = """
set("server.telnet",true)
set("request.grace_time", 1.0)
set("init.daemon.pidfile.path", "{pidfile.path}")
set("decoder.ffmpeg.codecs.alac", ["alac"])


# deeebuggin
set("log.file.path","{debug_log}")

# set up the stream
stream = crossfade(normalize(playlist.safe(
    id='stream',
    reload_mode='watch',
    mode='normal',
    '{playlist_root}/now_playing',
)))

# if source files don't contain metadata tags, use the filename
def apply_metadata(m) =
    title = m["title"]
    print("Now Playing: #{{m['filename']}}")
    if (title == "") then
        [("title", "#{{path.remove_extension(path.basename(m['filename']))}}")]
    else
        [("title", "#{{title}}")]
    end
end

# apply the metadata parser
stream = map_metadata(apply_metadata, stream)

# define the source. ignore errors and provide no infallibale fallback. yolo.
radio = fallback(track_sensitive=false, [stream])

# transcode to icecast
output.icecast(
  %mp3.vbr(quality=3),
  name='Croaker Radio',
  description='Background music for The Frog Hat Club',
  host="{icecast_host}",
  port={icecast_port},
  password="{icecast_password}",
  mount="{icecast_mount}",
  icy_metadata="true",
  url="{icecast_url}",
  fallible=true,
  radio
)
"""


def generate_liquidsoap_config():
    log = path.root() / "liquidsoap.log"
    if log.exists():
        log.unlink()
        log.touch()
    ls_config = path.root() / "croaker.liq"
    with ls_config.open("wt") as fh:
        fh.write(
            LIQUIDSOAP_CONFIG.format(
                pidfile=_pidfile(terminate_if_running=False),
                debug_log=log,
                playlist_root=path.playlist_root(),
                icecast_host=os.environ.get("ICECAST_HOST"),
                icecast_port=os.environ.get("ICECAST_PORT"),
                icecast_mount=os.environ.get("ICECAST_MOUNT"),
                icecast_password=os.environ.get("ICECAST_PASSWORD"),
                icecast_url=os.environ.get("ICECAST_URL"),
            )
        )
    path.playlist_root().mkdir(exist_ok=True)


def start_liquidsoap():
    logging.debug("Staring liquidsoap...")
    pf = _pidfile(terminate_if_running=False)
    pid = pf.read_pid()
    if not pid:
        logging.info("Liquidsoap does not appear to be running. Starting it...")
        generate_liquidsoap_config()
        Popen([os.environ["LIQUIDSOAP"], "--daemon", path.root() / "croaker.liq"])
        sleep(1)


def start():
    play_next("session_start")


def stop():
    _pidfile(terminate_if_running=True)


def play_next(playlist_name: str = None):
    start_liquidsoap()
    if playlist_name:
        pl = load_playlist(playlist_name)
        logging.debug(f"Loaded playlist {pl = }")
        if NOW_PLAYING != pl.name:
            _switch_to(pl)
    _send_liquidsoap_command("skip")


def _pidfile(terminate_if_running: bool = True):
    pf = os.environ.get("LIQUIDSOAP_PIDFILE", None)
    if pf:
        pf = Path(pf)
    else:
        pf = path.root() / "liquidsoap.pid"
    return pidfile(pf, terminate_if_running=terminate_if_running)


def _switch_to(playlist: Playlist):
    logging.debug(f"Switching to {playlist = }")
    np = path.playlist_root() / Path("now_playing")
    with np.open("wt") as fh:
        for track in playlist.tracks:
            fh.write(f"{track}\n")
    playlist.name


def _send_liquidsoap_command(command: str):
    conn = Telnet()
    conn.connect("localhost", port=1234)
    conn.send(f"Croaker_Radio.{command}\r")
    conn.send("quit\r")
    conn.close()
