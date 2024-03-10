from pathlib import Path
import subprocess
import logging

import ffmpeg

logger = logging.getLogger('transcoder')


def open(infile: Path):
    """
    Return a stream of mp3 data for the given path on disk.

    If the requested path is an mp3, return a filehandle on the file. Otherwise,
    invoke ffmpeg to tranascode whatever was requested to mp3 format and return
    a pipe to ffmpeg's STDOUT.
    """
    suffix = infile.suffix.lower()
    if suffix == '.mp3':
        logger.debug(f"Not transcoding mp3 {infile = }")
        return infile.open('rb')

    ffmpeg_args = (
        ffmpeg
        .input(str(infile))
        .output('-', format='mp3', q=2)
        .global_args('-hide_banner', '-loglevel', 'quiet')
        .compile()
    )

    # Force close STDIN to prevent ffmpeg from trying to read from it. silly ffmpeg.
    proc = subprocess.Popen(ffmpeg_args, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    proc.stdin.close()
    logger.debug(f"Spawned ffmpeg (PID {proc.pid}) with args {ffmpeg_args = }")
    return proc.stdout
