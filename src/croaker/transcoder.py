import logging
import subprocess
from io import BufferedReader
from pathlib import Path
from dataclasses import dataclass

import ffmpeg

logger = logging.getLogger("transcoder")


@dataclass
class FrameAlignedStream:
    """
    Use ffmpeg to transcode a source audio file to mp3 and iterate over the result
    in frame-aligned chunks. This will ensure that readers will always have a full
    frame of audio data to parse or emit.

    I learned a lot from https://github.com/pylon/streamp3 figuring this stuff out!

    Usage:

        >>> stream = FrameAlignedStream.from_source(Path('test.flac').open('rb'))
        >>> for segment in stream:
            ...
    """
    source: BufferedReader
    chunk_size:  int = 1024
    bit_rate: int = 192000
    sample_rate: int = 44100

    @property
    def frames(self):
        while True:
            frame = self._read_one_frame()
            if frame is None:
                return
            yield frame

    def _read_one_frame(self):
        """
        Read the next full audio frame from the input source and return it
        """

        # step through the source a byte at a time and look for the frame sync.
        header = None
        buffer = b''
        while not header:
            buffer += self.source.read(4 - len(buffer))
            if len(buffer) != 4:
                logging.debug("Reached the end of the source stream without finding another framesync.")
                return False
            header = buffer[:4]
            if header[0] != 0b11111111 or header[1] >> 5 != 0b111:
                logging.debug(f"Expected a framesync but got {buffer} instead; moving fwd 1 byte.")
                header = None
                buffer = buffer[1:]

        # Decode the mp3 header. We could derive the bit_rate and sample_rate
        # here if we had the lookup tables etc. from the MPEG spec, but since
        # we control the input, we can rely on them being predefined.
        version_code = (header[1] & 0b00011000) >> 3
        padding_code = (header[2] & 0b00000010) >> 1
        version = version_code & 1 if version_code >> 1 else 2
        is_padded = bool(padding_code)

        # calculate the size of the whole frame
        frame_size = 1152 if version == 1 else 576
        frame_size = self.bit_rate // 8 * frame_size // self.sample_rate
        if is_padded:
            frame_size += 1

        # read the rest of the frame from the source
        frame_data = self.source.read(frame_size - len(header))
        if len(frame_data) != frame_size - len(header):
            logging.debug("Reached the end of the source stream without finding a full frame.")
            return None

        # return the entire frame
        return header + frame_data

    def __iter__(self):
        """
        Generate approximately chunk_size segments of audio data by iterating over the
        frames, buffering them, and then yielding several as a single bytes object.
        """
        buf = b''
        for frame in self.frames:
            if len(buf) >= self.chunk_size:
                yield buf
                buf = b''
            if not frame:
                break
            buf += frame
        if buf:
            yield buf

    @classmethod
    def from_source(cls, infile: Path, **kwargs):
        """
        Create a FrameAlignedStream instance by transcoding an audio source on disk.
        """
        ffmpeg_args = (
            ffmpeg.input(str(infile))
            .output("pipe:",
                    map='a',
                    format="mp3",

                    # no ID3 headers -- saves having to decode them later
                    write_xing=0,
                    id3v2_version=0,

                    # force sasmple and bit rates
                    **{
                        'b:a': kwargs.get('bit_rate', cls.bit_rate),
                        'ar': kwargs.get('sample_rate', cls.sample_rate),
                    })
            .global_args("-hide_banner", "-vn")
            .compile()
        )

        # Force close STDIN to prevent ffmpeg from trying to read from it. silly ffmpeg.
        proc = subprocess.Popen(ffmpeg_args,
                                bufsize=kwargs.get('chunk_size', cls.chunk_size),
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)
        proc.stdin.close()
        logger.debug(f"Spawned ffmpeg (PID {proc.pid}) with args {ffmpeg_args = }")
        return cls(proc.stdout, **kwargs)
