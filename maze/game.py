#!/usr/bin/env python3
"""maze.exe — a community maze on the profile README. One issue = one move.

  PLAYER=octocat TITLE='maze|up' python3 maze/game.py   # play a move, print the issue reply
  python3 maze/game.py render                           # redraw svg + README from state
  python3 maze/game.py selftest
"""
import json, os, random, re, sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE, SVG, README = ROOT / "maze/state.json", ROOT / "maze/maze.svg", ROOT / "README.md"
PROFILE = "https://github.com/SwapnanilAdhikary"
W, H, CELL = 17, 7, 44
EXIT = (W - 1, H - 1)
DIRS = {"up": (0, -1, "↑"), "down": (0, 1, "↓"), "left": (-1, 0, "←"), "right": (1, 0, "→")}


def carve(seed):
    """Randomized Prim's: a perfect maze (a tree) as a set of open edges. Prim's branches a lot,
    so corridor auto-run still leaves ~14 decisions per escape (a backtracker's long corridors leave ~6)."""
    rng, edges, seen, frontier = random.Random(seed), set(), set(), [((0, 0), (0, 0))]
    while frontier:
        a, b = frontier.pop(rng.randrange(len(frontier)))
        if b in seen:
            continue
        seen.add(b)
        if a != b:
            edges.add(frozenset((a, b)))
        frontier += [(b, (b[0] + dx, b[1] + dy)) for dx, dy, _ in DIRS.values()
                     if 0 <= b[0] + dx < W and 0 <= b[1] + dy < H and (b[0] + dx, b[1] + dy) not in seen]
    return edges


def neighbours(edges, c):
    return [(c[0] + dx, c[1] + dy) for dx, dy, _ in DIRS.values() if frozenset((c, (c[0] + dx, c[1] + dy))) in edges]


def slide(edges, pos, d):
    """One step, then auto-run the corridor until a junction, dead end or the exit. None = wall."""
    nxt = (pos[0] + DIRS[d][0], pos[1] + DIRS[d][1])
    if frozenset((pos, nxt)) not in edges:
        return None
    path = [pos, nxt]
    while path[-1] != EXIT:
        ahead = [c for c in neighbours(edges, path[-1]) if c != path[-2]]
        if len(ahead) != 1:
            break
        path.append(ahead[0])
    return path[1:]


def distance(edges, start):
    dist, q = {start: 0}, deque([start])
    while q:
        c = q.popleft()
        for n in neighbours(edges, c):
            if n not in dist:
                dist[n] = dist[c] + 1
                q.append(n)
    return dist[EXIT]


def new_maze(s):
    s.update(seed=random.randrange(2**32), pos=[0, 0], trail=[[0, 0]])


def play(s, player, d):
    edges = carve(s["seed"])
    path = slide(edges, tuple(s["pos"]), d)
    if path is None:
        return f"💥 **Bonk.** There's a wall {DIRS[d][2]} of the cursor. It stays put. [Try another way]({PROFILE})."
    s["moves"] += 1
    stats = s["players"].setdefault(player, [0, 0])
    stats[0] += 1
    s["recent"] = ([[player, d]] + s["recent"])[:5]
    s["pos"] = list(path[-1])
    s["trail"] += [list(c) for c in path if list(c) not in s["trail"]]
    if path[-1] == EXIT:
        s["escapes"] += 1
        stats[1] += 1
        new_maze(s)
        return f"🏁 **You escaped!** That was escape #{s['escapes']}. A fresh maze has been carved. [Go look]({PROFILE})."
    left = distance(edges, path[-1])
    return f"🌈 Moved {DIRS[d][2]} {len(path)} cell{'s' * (len(path) > 1)}. The exit is **{left}** cells away. [Back to the maze]({PROFILE})."


def render_svg(s):
    edges = carve(s["seed"])
    ox, oy = (900 - W * CELL) // 2, 72
    walls = [f"M{ox} {oy}H{ox + W * CELL}M{ox} {oy}V{oy + H * CELL}"]
    trail = []
    for y in range(H):
        for x in range(W):
            X, Y = ox + x * CELL, oy + y * CELL
            if frozenset(((x, y), (x + 1, y))) not in edges:
                walls.append(f"M{X + CELL} {Y}V{Y + CELL}")
            if frozenset(((x, y), (x, y + 1))) not in edges:
                walls.append(f"M{X} {Y + CELL}H{X + CELL}")
            if [x, y] in s["trail"]:
                trail.append(f'<rect x="{X + 4}" y="{Y + 4}" width="{CELL - 8}" height="{CELL - 8}" rx="6"/>')
    ex, ey = ox + EXIT[0] * CELL, oy + EXIT[1] * CELL
    cx, cy = ox + s["pos"][0] * CELL + 14, oy + s["pos"][1] * CELL + 9
    last = f"last @{s['recent'][0][0]} {DIRS[s['recent'][0][1]][2]}" if s["recent"] else "waiting for player 1"
    status = f"moves {s['moves']} · escapes {s['escapes']} · exit {distance(edges, tuple(s['pos']))} away · {last}"
    SVG.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="440" viewBox="0 0 900 440" role="img" aria-labelledby="t">
  <title id="t">maze.exe: a community maze. The rainbow cursor is {status}.</title>
  <defs>
    <linearGradient id="rb" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#ff7b72"/><stop offset=".25" stop-color="#f2cc60"/><stop offset=".5" stop-color="#7ee787"/><stop offset=".75" stop-color="#79c0ff"/><stop offset="1" stop-color="#d2a8ff"/>
    </linearGradient>
    <linearGradient id="bar" x1="0" x2="1">
      <stop offset="0" stop-color="#ff7b72"/><stop offset=".2" stop-color="#ffa657"/><stop offset=".4" stop-color="#f2cc60"/><stop offset=".6" stop-color="#7ee787"/><stop offset=".8" stop-color="#79c0ff"/><stop offset="1" stop-color="#d2a8ff"/>
    </linearGradient>
    <clipPath id="win"><rect width="900" height="440" rx="12"/></clipPath>
  </defs>
  <style>
    .m{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}
    @keyframes pulse{{50%{{opacity:.35}}}}
    .exit{{animation:pulse 1.6s ease-in-out infinite}}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
  </style>
  <g clip-path="url(#win)">
    <rect width="900" height="440" fill="#0d1117"/>
    <rect width="900" height="44" fill="#161b22"/>
    <rect y="44" width="900" height="3" fill="url(#bar)"/>
    <circle cx="26" cy="22" r="7" fill="#ff5f56"/><circle cx="50" cy="22" r="7" fill="#ffbd2e"/><circle cx="74" cy="22" r="7" fill="#27c93f"/>
    <text x="450" y="28" text-anchor="middle" class="m" font-size="15" fill="#8b949e">maze.exe — Pldjkfgew@345</text>
  </g>
  <rect x=".5" y=".5" width="899" height="439" rx="12" fill="none" stroke="#30363d"/>
  <g fill="#7ee787" opacity=".09">{"".join(trail)}</g>
  <g class="exit"><rect x="{ex + 4}" y="{ey + 4}" width="{CELL - 8}" height="{CELL - 8}" rx="6" fill="#7ee787" opacity=".25" stroke="#7ee787"/>
    <text x="{ex + CELL / 2}" y="{ey + CELL / 2 + 4}" text-anchor="middle" class="m" font-size="11" font-weight="700" fill="#7ee787">EXIT</text></g>
  <path d="{"".join(walls)}" stroke="#8b949e" stroke-width="3" stroke-linecap="round" fill="none"/>
  <polygon transform="translate({cx} {cy})" points="0,0 0,22 6,17 10,26 14,24 10,15 18,15" fill="url(#rb)" stroke="#0d1117" stroke-width="1.5" stroke-linejoin="round"/>
  <text x="{ox}" y="416" class="m" font-size="15"><tspan fill="#7ee787">➜</tspan> <tspan fill="#c9d1d9">{status}</tspan></text>
</svg>
''')


def render_readme(s):
    who = lambda u: f'<a href="https://github.com/{u}">@{u}</a>'
    recent = " · ".join(f"{who(u)} {DIRS[d][2]}" for u, d in s["recent"]) or "nobody yet. Be player one!"
    top = sorted(s["players"].items(), key=lambda kv: (-kv[1][1], -kv[1][0]))[:5]
    board = " · ".join(f"{who(u)} {m}{f' 🏁{e}' if e else ''}" for u, (m, e) in top) or "empty"
    block = f"""<!-- MAZE:START -->
<p align="center"><img src="maze/maze.svg?v={s['moves']}" width="100%" alt="maze.exe: {s['moves']} moves and {s['escapes']} escapes so far" /></p>
<p align="center"><sub><b>recent</b> {recent}<br/><b>top explorers</b> {board}</sub></p>
<!-- MAZE:END -->"""
    text = README.read_text()
    README.write_text(re.sub(r"<!-- MAZE:START -->.*?<!-- MAZE:END -->", lambda _: block, text, flags=re.S))


def selftest():
    for seed in range(200):
        edges = carve(seed)
        assert len(edges) == W * H - 1  # spanning tree: every cell reachable, no loops
        assert distance(edges, (0, 0)) > 0
    s = {"seed": 7, "pos": [0, 0], "trail": [[0, 0]], "moves": 0, "escapes": 0, "recent": [], "players": {}}
    edges = carve(7)
    # Walk the maze by always taking the direction that gets closer; it must escape.
    for _ in range(200):
        pos = tuple(s["pos"])
        d = min((d for d in DIRS if slide(edges, pos, d)), key=lambda d: distance(edges, slide(edges, pos, d)[-1]))
        if "escaped" in play(s, "tester", d):
            break
    assert s["escapes"] == 1 and s["pos"] == [0, 0] and s["players"]["tester"][1] == 1
    blocked = next(d for d in DIRS if slide(carve(s["seed"]), (0, 0), d) is None)
    assert "Bonk" in play(s, "tester", blocked) and s["pos"] == [0, 0]
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        sys.exit(selftest())
    s = json.loads(STATE.read_text()) if STATE.exists() else {"moves": 0, "escapes": 0, "recent": [], "players": {}}
    if "seed" not in s:
        new_maze(s)
    if sys.argv[1:] != ["render"]:
        player, title = os.environ["PLAYER"], os.environ["TITLE"]
        d = title.partition("|")[2].strip().lower()
        if d not in DIRS or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", player):
            sys.exit(print("🤔 I only understand `maze|up`, `maze|down`, `maze|left` and `maze|right`.") or 0)
        print(play(s, player, d))
    STATE.write_text(json.dumps(s) + "\n")
    render_svg(s)
    render_readme(s)
