#!/usr/bin/env python3
"""바탕화면 GRAIN.app 을 만든다. 아이콘은 앱 로고와 같은 도형을 그린다.

    python3 desktop/build_app.py

인터넷이 되면 배포판을 열고, 안 되면 앱 안에 든 오프라인 사본을 연다.
docs/ 를 고쳤으면 다시 실행해서 오프라인 사본을 갱신할 것.
"""
import plistlib, re, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
APP = Path.home() / "Desktop" / "GRAIN.app"
URL = "https://won2070-commits.github.io/gyeol/"

INK, PAPER, LIME = (23, 26, 18), (243, 244, 238), (203, 242, 75)
SS = 4                      # 초과표본배율: 4배로 그린 뒤 줄여서 계단 제거
SIZE, MARGIN, UNIT = 1024, 100, 40   # 824px 안에 SVG 40단위를 담는다

# docs/app.js 의 브랜드 마크와 같은 좌표 (viewBox 0 0 40 40)
ARCS = [  # (시작점, 제어점1, 제어점2, 끝점, 불투명도)
    ((12.5, 9.0), (20.0, 13.6), (20.0, 26.4), (12.5, 31.0), 1.00),
    ((20.0, 6.5), (30.0, 12.1), (30.0, 27.9), (20.0, 33.5), 0.55),
    ((27.5, 4.5), (39.5, 11.0), (39.5, 29.0), (27.5, 35.5), 0.28),
]
STROKE, DOT, DOT_R = 2.6, (11.0, 20.0), 2.7
RADIUS = 11.0


def blend(top, bottom, a):
    return tuple(round(b + (t - b) * a) for t, b in zip(top, bottom))


def bezier(p0, c1, c2, p3, steps=180):
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((
            u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1],
        ))
    return out


def draw_icon(path):
    n = SIZE * SS
    scale = (SIZE - 2 * MARGIN) * SS / UNIT          # 단위 → 픽셀
    off = MARGIN * SS
    to_px = lambda p: (off + p[0] * scale, off + p[1] * scale)

    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([off, off, n - off, n - off], radius=RADIUS * scale, fill=INK + (255,))

    for p0, c1, c2, p3, alpha in ARCS:
        color = blend(PAPER, INK, alpha) + (255,)
        r = STROKE * scale / 2
        # 원 브러시를 촘촘히 찍는다. 폴리라인 두께로 그리면 곡선 바깥쪽에 톱니가 생긴다.
        for x, y in bezier(p0, c1, c2, p3, steps=1600):
            px, py = to_px((x, y))
            d.ellipse([px - r, py - r, px + r, py + r], fill=color)

    cx, cy = to_px(DOT)
    r = DOT_R * scale
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=LIME + (255,))

    img.resize((SIZE, SIZE), Image.LANCZOS).save(path)


def offline_copy():
    """ES 모듈은 file:// 에서 import 가 막히므로 한 파일로 합쳐 둔다."""
    html = (DOCS / "index.html").read_text()
    data = re.sub(r"^export ", "", (DOCS / "data.js").read_text(), flags=re.M)
    app = (DOCS / "app.js").read_text()
    app = re.sub(r"^import .*?;\n", "", app, count=1, flags=re.M)   # 첫 줄 import 제거
    css = (DOCS / "style.css").read_text()

    html = re.sub(r'<link rel="stylesheet" href="style\.css[^"]*">', f"<style>{css}</style>", html)
    html = re.sub(r'<script type="module" src="app\.js[^"]*"></script>', "", html)
    html = html.replace("</body>", f'<script type="module">{data}\n{app}</script></body>')
    return html


def main():
    assert DOCS.is_dir(), DOCS
    if APP.exists():
        shutil.rmtree(APP)
    (APP / "Contents" / "MacOS").mkdir(parents=True)
    res = APP / "Contents" / "Resources"
    res.mkdir()

    iconset = res / "app.iconset"
    iconset.mkdir()
    master = iconset / "icon_512x512@2x.png"
    draw_icon(master)
    for size in (16, 32, 128, 256, 512):
        for suffix, px in ((f"icon_{size}x{size}.png", size), (f"icon_{size}x{size}@2x.png", size * 2)):
            if not (iconset / suffix).exists():
                Image.open(master).resize((px, px), Image.LANCZOS).save(iconset / suffix)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(res / "app.icns")], check=True)
    shutil.rmtree(iconset)

    (res / "offline.html").write_text(offline_copy())

    (APP / "Contents" / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleName": "GRAIN", "CFBundleDisplayName": "GRAIN",
        "CFBundleIdentifier": "com.haengchuk.grain",
        "CFBundleVersion": "1.0", "CFBundleShortVersionString": "1.0",
        "CFBundlePackageType": "APPL", "CFBundleExecutable": "GRAIN",
        "CFBundleIconFile": "app", "LSMinimumSystemVersion": "10.13",
    }))

    launcher = APP / "Contents" / "MacOS" / "GRAIN"
    launcher.write_text(f"""#!/bin/bash
# 인터넷이 되면 항상 최신 배포판을 연다(업데이트 자동 반영). 안 되면 앱 안에 든 사본으로 실행.
OFFLINE="$(cd "$(dirname "$0")/../Resources" && pwd)/offline.html"
URL="{URL}"
if curl -s -o /dev/null --max-time 2 "$URL"; then TARGET="$URL"; else TARGET="file://$OFFLINE"; fi
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || CHROME="$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ -x "$CHROME" ]; then
  "$CHROME" --app="$TARGET" --window-size=1180,860 >/dev/null 2>&1 &
else
  open "$TARGET"
fi
""")
    launcher.chmod(0o755)
    refresh_finder()
    print("만들었습니다:", APP)


def refresh_finder():
    """Finder 는 앱을 한 번 그리면 아이콘을 캐시한다. 다시 빌드했으면 강제로 갱신해야
    옛 아이콘이 그대로 남지 않는다."""
    subprocess.run(["touch", str(APP)], check=True)
    lsregister = ("/System/Library/Frameworks/CoreServices.framework/Frameworks"
                  "/LaunchServices.framework/Support/lsregister")
    if Path(lsregister).exists():
        subprocess.run([lsregister, "-f", str(APP)], timeout=60, check=False)
    subprocess.run(["killall", "Finder"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
