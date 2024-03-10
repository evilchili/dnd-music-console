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

Because I run an online D&amp;D game, which includes a background music stream for my players. The stream used to be served by liquidsoap and controlled by a bunch of bash scripts I cobbled together which are functional but brittle, and liquidsoap is a nightmare for the small use case. Also, this currently requires me to have a terminal window open to my media server to control liquidsoap directly, and I'd rather integrate the music controls directly with the rest of my DM tools, all of which run on my laptop.

*Now that is a powerful yak! -- Aesop Rock (misquoted)*


## Quick Start (Server)

This assumes you have a functioning icecast2 installation already.

```
% sudo apt install libshout3-dev
% mkdir -p ~/.dnd/croaker
% croaker setup > ~/.dnd/croaker/defaults
% vi ~/.dnd/croaker/defaults  # adjust to taste
% croaker add session_start /music/session_start.mp3
% croaker add battle /music/battle/*.mp3
```

Now start the server, which will begin streaming the `session_start` playlist:

```
% croaker start
INFO Daemonizing controller on (localhost, 8003); pidfile and logs in ~/.dnd/croaker
```

Connnect to the command &amp; control server:

```
% telnet localhost 8003
*Trying 127.0.0.1...*
*Connected to croaker.local.*
*Escape character is '^]'.*
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
FFWD
OK
```

Stop the music:

```
STOP
OK
```

Disconnect:

```
kthx
KBAI
Connection closed by foreign host.
```
