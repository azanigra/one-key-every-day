# One key every day

Short vertical videos (1080×1920, 15 s) that teach one Omarchy keyboard
shortcut each, drawn as vector graphics and rendered with `rsvg-convert` and
`ffmpeg`.

By Pablo Barrera. Videos licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): share and adapt
freely, with credit.

```sh
python3 make.py frames/    # renders frames/0000.png …
ffmpeg -framerate 30 -i frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart videos/one-key-01-super-enter.mp4
```
