#!/usr/bin/env python3
"""글에 넣을 이미지를 WebP로 변환해 assets/img/posts/<슬러그>/ 에 넣는다.

깃 저장소는 한번 커밋한 파일을 히스토리에 계속 들고 있어서, 나중에 지워도
용량이 줄지 않는다. 그래서 원본 PNG를 그대로 커밋하지 않고 여기를 거친다.

쓰는 법:
    python3 tools/optimize-image.py <슬러그> <이미지...>
    python3 tools/optimize-image.py giscus-category-id ~/Desktop/shot1.png

    --width N   최대 가로 폭 (기본 1400)
    --quality N WebP 품질 (기본 82)
    --keep-png  WebP 대신 PNG로 저장 (투명도가 꼭 필요할 때)

필요한 것: pip install Pillow
"""

import argparse
import pathlib
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow가 필요합니다:  pip install Pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "img" / "posts"


def main() -> int:
    ap = argparse.ArgumentParser(description="글 이미지를 WebP로 변환해 저장한다")
    ap.add_argument("slug", help="글 슬러그 (파일명에서 날짜를 뺀 부분)")
    ap.add_argument("images", nargs="+", help="변환할 이미지 경로")
    ap.add_argument("--width", type=int, default=1400, help="최대 가로 폭 (기본 1400)")
    ap.add_argument("--quality", type=int, default=82, help="WebP 품질 (기본 82)")
    ap.add_argument("--keep-png", action="store_true", help="PNG로 저장")
    args = ap.parse_args()

    out_dir = DEST / args.slug
    out_dir.mkdir(parents=True, exist_ok=True)

    before = after = 0
    written = []

    for src in args.images:
        p = pathlib.Path(src).expanduser()
        if not p.is_file():
            print(f"  건너뜀 (없는 파일): {p}", file=sys.stderr)
            continue

        im = Image.open(p)
        w0, h0 = im.size
        s0 = p.stat().st_size

        if w0 > args.width:
            im = im.resize((args.width, round(h0 * args.width / w0)), Image.LANCZOS)

        ext = "png" if args.keep_png else "webp"
        dst = out_dir / f"{p.stem}.{ext}"
        if args.keep_png:
            im.save(dst, "PNG", optimize=True)
        else:
            im.convert("RGB").save(dst, "WEBP", quality=args.quality, method=6)

        s1 = dst.stat().st_size
        before += s0
        after += s1
        written.append(dst)
        print(f"  {p.name}  {w0}px {s0 // 1024}KB  →  {im.size[0]}px {s1 // 1024}KB")

    if not written:
        print("변환한 파일이 없습니다.", file=sys.stderr)
        return 1

    saved = 100 - after * 100 // before if before else 0
    print(f"\n{len(written)}개, {before // 1024}KB → {after // 1024}KB ({saved}% 절감)")
    print(f"저장 위치: {out_dir.relative_to(ROOT)}\n")

    print("글 front matter에 넣을 것:")
    print(f"  media_subpath: /assets/img/posts/{args.slug}/\n")
    print("본문에서 참조:")
    for d in written:
        print(f"  ![설명]({d.name})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
