# utility-scripts

Personal collection of global CLI utilities, installed on `$PATH` and runnable from anywhere.

## Setup

Clone anywhere and add to `$PATH`:

```bash
git clone https://github.com/FayazK/utility-scripts.git ~/.scripts
export PATH="$HOME/.scripts:$PATH"   # add to ~/.zshrc or ~/.bashrc
```

Scripts are self-executable — no `python` prefix or `.py` extension. A Python 3 environment with the script's dependencies must be available (see each script for requirements).

## Scripts

### `nano-banana`

Generate images via Google's Nano Banana (Gemini image-generation) models — text-to-image or image+text-to-image with reference images.

**Requires:** `google-genai`, `pillow`, and `GEMINI_API_KEY` exported.

```bash
nano-banana "A photorealistic ginger cat wearing a wizard hat" \
  -o ./out -m 2 -s 2K -a 1:1
```

| Flag | Description |
|---|---|
| `prompt` | Text prompt (positional, required) |
| `-o, --output-dir` | Directory to write PNG(s) into (required) |
| `-m, --model` | `2` = Nano Banana 2 (Flash, default), `pro` = Nano Banana Pro |
| `-s, --size` | `1K`, `2K` (default), or `4K` |
| `-a, --aspect-ratio` | e.g. `1:1` (default), `16:9`, `9:16`, `3:2`, `21:9` |
| `-r, --reference` | Path to a reference image. Repeat for multiple (up to 14). |
| `-n, --name` | Output filename stem (defaults to timestamp) |

See `nano-banana --help` for full usage.

## Conventions

See [`CLAUDE.md`](./CLAUDE.md) for script-authoring conventions used in this repo.
