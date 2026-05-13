#!/usr/bin/env python3
"""Smoke test: pygbag build servido localmente — clique UME + 1.º personagem, screenshot e amostra de pixels."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Instale: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:9876/", help="URL do build/web")
    ap.add_argument("--out", type=Path, default=Path("/tmp/pygbag-playwright.png"))
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
        )
        page = ctx.new_page()
        page.set_default_timeout(180_000)
        page.goto(args.url, wait_until="domcontentloaded")
        page.wait_for_selector("canvas#canvas", state="visible", timeout=180_000)

        def log_console(msg) -> None:
            try:
                print(f"[browser] {msg.type}: {msg.text}")
            except Exception:
                pass

        page.on("console", log_console)

        # UME: gesto no próprio canvas (pygbag regista MM.UME)
        canvas = page.locator("canvas#canvas")
        box = canvas.bounding_box()
        if box:
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            print(f"canvas bbox {box!r} click ({cx:.0f},{cy:.0f})")
            page.mouse.click(cx, cy)
        else:
            page.mouse.click(195, 422)

        # Descarregar WASM + extrair apk + arrancar main.py pode levar >20s em CI
        page.wait_for_timeout(45_000)

        # Menu: 1.º cartão (personagem)
        page.mouse.click(180, 120)
        page.wait_for_timeout(5_000)

        args.out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(args.out), type="png")
        canvas_only = args.out.with_name(args.out.stem + "_canvas.png")
        try:
            canvas.screenshot(path=str(canvas_only))
            print(f"canvas-only -> {canvas_only}")
        except Exception as e:
            print(f"canvas screenshot skip: {e}")

        browser.close()

    # Amostra de cor no centro (não deve ser só powderblue 176,224,230 em jogo a correr)
    try:
        from PIL import Image

        im = Image.open(args.out)
        px = im.load()
        w, h = im.size
        samples = [(w // 2, h // 2), (w // 2, 80), (30, 400)]
        print(f"viewport screenshot {args.out} size={im.size}")
        for x, y in samples:
            if x < w and y < h:
                print(f"  pixel ({x},{y}) = {px[x, y]}")
        cpath = args.out.with_name(args.out.stem + "_canvas.png")
        if cpath.is_file():
            im2 = Image.open(cpath)
            p2 = im2.load()
            w2, h2 = im2.size
            print(f"canvas-only {cpath} size={im2.size}")
            for x, y in [(w2 // 2, h2 // 2), (w2 // 2, 40), (20, h2 // 2)]:
                if x < w2 and y < h2:
                    print(f"  pixel ({x},{y}) = {p2[x, y]}")
    except Exception as e:
        print(f"screenshot salvo em {args.out} (PIL opcional: {e})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
