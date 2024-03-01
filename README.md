# Croaker
A command-and-control web application for icecast / liquidaudio, with helpers for D&amp;D session music.

## What? Why?

Because I run an online D&amp;D game, which includes a background music stream for my players. The stream is controlled by a bunch of bash scripts I cobbled together which are functional but brittle. Also, this currently requires me to have a terminal window open to my media server to control liquidsoap directly, and I'd rather integrate the music controls directly with the rest of my DM tools, all of which run on my laptop. A web-based commmand-and-control app lets me use vanilla HTTP requests to control liquidsoap.

*Now that is a powerful yak! -- Aesop Rock (misquoted)*


## Quick Start (Server)

This assumes you have a functioning icecast2 installation already.

```
% mkdir -p ~/.dnd/croaker
% croaker setup > ~/.dnd/croaker/defaults
% vi ~/.dnd/croaker/defaults  # adjust to taste
% croaker add session_start /music/session_start.mp3
% croaker add battle /music/battle/*.mp3
```

Now start the server, which will begin streaming the `session_start` playlist:

```
% croaker start
Daemonizing webserver on http://0.0.0.0:8003, pidfile and output in ~/.dnd/croaker
```

## Quick Start (Client)
```
% mkdir -p ~/.dnd/croaker
% croaker setup > ~/.dnd/croaker/defaults  # only the client config is required
% vi ~/.dnd/croaker/defaults  # adjust to taste
```

Switch to battle music -- roll initiative!

```
% croaker play battle
OK
```

Skip this track and move on to the next:

```
% croaker skip
OK
```

Stop the server:

```
% croaker stop
OK
```
