# One key every day

Short vertical videos (1080×1920, 15 s) that teach one Omarchy keyboard
shortcut each, drawn as vector graphics and rendered with `rsvg-convert` and
`ffmpeg`.

| # | Keys | What it does | Video |
| --- | --- | --- | --- |
| 1 | Super + Enter | Opens a terminal | [mp4](videos/one-key-01-super-enter.mp4) |
| 2 | Super + Space | Opens the Omarchy menu | [mp4](videos/one-key-02-super-space.mp4) |

Shortcuts are checked against Omarchy 4.5 defaults.

## Render an episode

Needs `python3`, `rsvg-convert` (librsvg), `ffmpeg` and the JetBrainsMono Nerd
Font, all present on a stock Omarchy install.

```sh
python3 make.py 2 frames/        # renders frames/0000.png … 0449.png
ffmpeg -framerate 30 -i frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart videos/one-key-02-super-space.mp4
python3 make.py 2 --cover videos/one-key-02-cover.png
```

## Add an episode

Add an entry to `EPISODES` in `make.py`: the question, the two keys, a scene
function for what appears once the keys land, the caption and tomorrow's
teaser. `scene_terminal` and `scene_menu` are the examples to copy.

## License

By Pablo Barrera. Videos and images licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): share and adapt
freely, with credit. The code (`make.py`) is under the [MIT License](LICENSE).
