# treeled
scratch pad &amp; notes on neopixels &amp; fadecandy setup

## setup

on a fresh raspberry pi
```
$ sudo apt install vim tmux git
```

download this repo & fadecandyserver (forked a private repo fork that currently works)
```
$ git clone git@github.com:algrant/treeled
$ git clone git@github.com:algrant/fadecandyserver.git
```

make fadecandyserver
```
$ cd fadecadyserver
$ make
$ cd ..
```
open tmux
```
$ tmux
```

recall you can turn on mouse mode with
```
crtl+b :set mouse
```

run fadecandyserver with treeled config (just specifies to not worry about being exactly on localhost)
```
$ sudo ./fadecandyserver/fcserver treeled/config.json
```

In an appropriate browser visit
treeled.local:7890

and you'll be able to test that everything is working.


