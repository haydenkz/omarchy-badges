#!/usr/bin/env python3
"""Omarchy 88x31 badges, one per default theme, at several nearest-neighbour sizes.

    python3 build.py           # render badges/ from themes.json
    python3 build.py --fetch   # refresh themes.json from omarchy.org first

Colours are omarchy.org's per-theme CSS vars, so each badge matches the site in that theme.
The wordmark uses the same stepped bands the site draws it with (crest > hover > lit > mid > dim).
logo.txt is /usr/share/omarchy/logo.svg thresholded to 81x19. Needs ImageMagick 7 (`magick`).
"""
import json, re, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "badges"
W, H = 88, 31
SCALES = [1, 2, 3, 4, 10]
VARS = ["field-bg", "border-strong", "bg-deep", "text-muted", "field-crest", "field-hover", "field-lit", "field-mid", "field-dim"]

logo = [l.strip() for l in open(ROOT / "logo.txt") if l.strip()]

# 3x5 pixel font for "POWERED BY" (W is wider so it reads)
F = {
    "P": ["##.", "#.#", "##.", "#..", "#.."],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."],
    "W": ["#...#", "#...#", "#.#.#", "#.#.#", ".#.#."],
    "E": ["###", "#..", "##.", "#..", "###"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "B": ["##.", "#.#", "##.", "#.#", "##."],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    " ": ["...", "...", "...", "...", "..."],
}
TEXT = "POWERED BY"

# logo row -> band, measured off omarchy.org/brand/social/solitude.png
BANDS = ["field-crest"] * 5 + ["field-hover"] * 2 + ["field-lit"] * 4 + ["field-mid"] * 3 + ["field-dim"] * 5

# The site's minifier swaps hex for a name when it's shorter.
NAMED = {"silver": "#c0c0c0", "gray": "#808080", "grey": "#808080", "white": "#ffffff", "black": "#000000",
         "tan": "#d2b48c", "linen": "#faf0e6", "wheat": "#f5deb3", "beige": "#f5f5dc", "ivory": "#fffff0",
         "snow": "#fffafa", "azure": "#f0ffff", "khaki": "#f0e68c", "plum": "#dda0dd", "orchid": "#da70d6"}


def hx(s):
    s = NAMED.get(s, s)
    if re.fullmatch(r"#[0-9a-fA-F]{3}", s):
        s = "#" + "".join(c * 2 for c in s[1:])
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        sys.exit(f"can't parse colour {s!r}")
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t): return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def get(url):
    # omarchy.org 403s urllib's default user agent
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"})).read().decode()


def fetch_themes():
    html = get("https://omarchy.org")
    css = "".join(get("https://omarchy.org" + href)
                  for href in sorted(set(re.findall(r'href="(/_astro/[^"]+\.css)"', html))))
    themes = {}
    for name, body in re.findall(r"\[data-theme=([a-z0-9-]+)\]\{([^}]*)\}", css):
        v = dict(re.findall(r"--t-([a-z0-9-]+):([^;]+)", body))
        if all(k in v for k in VARS):
            themes[name] = {k: v[k] for k in VARS}
    if not themes:
        sys.exit("no themes found in omarchy.org CSS")
    (ROOT / "themes.json").write_text(json.dumps(dict(sorted(themes.items())), indent=2) + "\n")
    print(f"themes.json: {len(themes)} themes")


def frame(t, shine_x):
    px = [[t["field-bg"]] * W for _ in range(H)]
    for x in range(W): px[0][x] = t["border-strong"]; px[H - 1][x] = t["bg-deep"]
    for y in range(H): px[y][0] = t["border-strong"]; px[y][W - 1] = t["bg-deep"]
    lx, ly = 3, 10
    tx, ty = lx, 3
    for ch in TEXT:
        for r, row in enumerate(F[ch]):
            for c, v in enumerate(row):
                if v == "#": px[ty + r][tx + c] = t["text-muted"]
        tx += len(F[ch][0]) + 1
    for r, row in enumerate(logo):
        for c, v in enumerate(row):
            if v != "1": continue
            col = t[BANDS[r]]
            if shine_x is not None:
                d = abs((c + r * 0.5) - shine_x)
                # stepped, keeps the gif palette small
                if d < 4: col = mix(col, t["field-crest"], round((1 - d / 4) * 4) / 4)
            px[ly + r][lx + c] = col
    return px


def write_ppm(px, path):
    with open(path, "w") as f:
        f.write(f"P3\n{W} {H}\n255\n")
        for row in px: f.write(" ".join(f"{r} {g} {b}" for r, g, b in row) + "\n")


def build(name, raw, tmp):
    t = {k: hx(v) for k, v in raw.items()}
    frames = tmp / name
    frames.mkdir()
    # a 3s still, then a shine sweeps across the wordmark
    write_ppm(frame(t, None), frames / "00.ppm")
    for i, s in enumerate(range(-6, 100, 7)):
        write_ppm(frame(t, s), frames / f"{i + 1:02d}.ppm")
    for k in SCALES:
        d = OUT / f"{W * k}x{H * k}"
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run(["magick", "-delay", "5", *sorted(map(str, frames.glob("*.ppm"))), "-loop", "0",
                        "-set", "delay", "%[fx:t==0?300:5]", "-scale", f"{k * 100}%", d / f"{name}.gif"], check=True)
        subprocess.run(["magick", frames / "00.ppm", "-scale", f"{k * 100}%", d / f"{name}.png"], check=True)


def main():
    if "--fetch" in sys.argv:
        fetch_themes()
    themes = json.loads((ROOT / "themes.json").read_text())
    shutil.rmtree(OUT, ignore_errors=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, raw in themes.items():
            build(name, raw, Path(tmp))
            print(name)


if __name__ == "__main__":
    main()
