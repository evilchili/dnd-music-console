# Croaker

A shoutcast audio player designed for serving D&amp;D session music.

### Features

* Native streaming of MP3 sources direct to your shoutcast / icecast server
* Transcoding of anything your local `ffmpeg` installation can convert to mp3
* Playlists are built using symlinks
* Randomizes playlist order the first time it is cached
* Always plays `_theme.mp3` first upon switching to a playlist, if it exists
* Falls back to silence if the stream encounters an error

### Requirements

* A functioning shoutcast / icecast server
* Python >= 3.10
* ffmpeg
* libshout3-dev


## What? Why?

Because I run an online D&amp;D game, which includes a background music stream for my players. The stream used to be served by liquidsoap and controlled by a bunch of bash scripts I cobbled together which are functional but brittle, and liquidsoap is a nightmare for the small use case. Also, this required me to have a terminal window open to my media server to control liquidsoap directly, and I'd rather integrate the music controls directly with the rest of my DM tools, all of which run on my laptop.

*Now that is a powerful yak! -- Aesop Rock (misquoted)*


## Quick Start (Server)

This assumes you have a functioning icecast2/whatever installation already.

```
% sudo apt install libshout3-dev
% mkdir -p ~/.dnd/croaker
% croaker setup > ~/.dnd/croaker/defaults
% vi ~/.dnd/croaker/defaults  # adjust to taste
% croaker add session_start /music/session_start.mp3
% croaker add battle /music/battle/*.mp3
```

Now start the server, which will begin streaming the `session_start` playlist:

## Controlling The Server

```
% croaker start
INFO Daemonizing controller on (localhost, 8003); pidfile and logs in ~/.dnd/croaker
```

Connnect to the command &amp; control server:

```bash
% telnet localhost 8003
Trying 127.0.0.1...
Connected to croaker.local.
Escape character is '^]'.

help

PLAY PLAYLIST    - Switch to the specified playlist.
LIST [PLAYLIST]  - List playlists or contents of the specified list.
FFWD             - Skip to the next track in the playlist.
HELP             - Display command help.
KTHX             - Close the current connection.
STOP             - Stop the current track and stream silence.
STFU             - Terminate the Croaker server.
```

List available playlists:

```
list

battle
adventure
session_start
```

Switch to battle music -- roll initiative!
```
play battle
OK
```

Skip this track and move on to the next:

```
ffwd
OK
```

Stop the music:

```
stop
OK
```

Disconnect:

```
kthx
KBAI
Connection closed by foreign host.
```

## Python Client Implementation

Here's a sample client using Ye Olde Socket Library:

```python
import socket
from dataclasses import dataclass
from functools import cached_property


@dataclass
class CroakerClient():
    host: str
    port: int

    @cached_property
    def playlists(self):
        return self.send("LIST").split("\n")

    def list(self, *args):
        if not args:
            return self.playlists
        return self.send(f"LIST {args[0]}")

    def play(self, *args):
        if not args:
            return "Error: Must specify the playlist to play."
        return self.send(f"PLAY {args[0]}")

    def ffwd(self, *args):
        return self.send("FFWD")

    def stop(self, *args):
        return self.send("STOP")

    def send(self, msg: str):
        BUFSIZE = 4096
        data = bytearray()
        with socket.create_connection((self.host, self.port)) as sock:
            sock.sendall(f"{msg}\n".encode())
            while True:
                buf = sock.recv(BUFSIZE)
                data.extend(buf)
                if len(buf) < BUFSIZE:
                    break
            sock.sendall(b'KTHX\n')
        return data.decode()


if __name__ == '__main__':
    client = CroakerClient(host='localhost', port=1234)
    client.play('session_start')
```
