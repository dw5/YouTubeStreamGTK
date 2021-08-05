# <a href="https://source.puri.sm/todd/Stream"><img height="32" src="https://github.com/dw5/YouTubeStreamGTK/raw/master/data/icons/hicolor/scalable/apps/sm.puri.Stream.svg" /> Stream</a>

Search, Watch, Download YouTube videos (and as audio) on your Pinephone / Librem 5
Provides Video and Search history.
No ability to "subscribe" to channels, or have a feed for it yet.

![screenshot](https://github.com/dw5/YouTubeStreamGTK/raw/master/screenshots/20210805_18h44m51s_grim.png)
![screenshot](https://github.com/dw5/YouTubeStreamGTK/raw/master/screenshots/20210805_18h46m21s_grim.png)
![screenshot](https://github.com/dw5/YouTubeStreamGTK/raw/master/data/screenshots/sm.puri.Stream.3.png)

# Building on different distributions

**Note**: these are illustrative instructions. If you're a developer or a package maintainer, they
can be useful to you. If not, just install the flatpak.

## Building on Ubuntu/Debian ("PureOS")

```bash
sudo apt-get install python-requests

git clone https://source.puri.sm/todd/Stream
cd Stream
mkdir build
cd build
meson ..
meson configure -Dprefix=$PWD/testdir # use this line if you want to avoid installing system wide
ninja
(sudo) ninja install
```

## Building on Arch/Manjaro

```bash
sudo pacman -S python-requests python-gobject

git clone https://source.puri.sm/todd/Stream
cd Stream
mkdir build
cd build
meson ..
meson configure -Dprefix=$PWD/testdir # use this line if you want to avoid installing system wide
ninja
(sudo) ninja install
```
