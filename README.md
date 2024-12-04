# treeled
scratch pad &amp; notes on neopixels &amp; fadecandy setup

## setup

on a fresh raspberry pi
```
sudo apt install vim tmux git
```

download this repo & fadecandyserver (forked a private repo fork that currently works)
```
git clone git@github.com:algrant/treeled
git clone git@github.com:algrant/fadecandyserver.git
```

make fadecandyserver
```
cd fadecadyserver
make
cd ..
```

run fadecandyserver with treeled config (just specifies to not worry about being exactly on localhost)
```
./fadecandyserver/fcserver treeled/config.json
```
