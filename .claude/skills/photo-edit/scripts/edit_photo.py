# -*- coding: utf-8 -*-
"""
photo-edit: 밝기/대비/색조 보정 + 리사이즈 + 비율 중앙 크롭을 하는 CLI 스크립트 (Pillow 기반)

사용법:
    python edit_photo.py <입력파일_또는_폴더> [옵션들]

옵션:
    --out-dir DIR       결과 저장 폴더 (기본: 입력 위치 옆에 "edited" 폴더 새로 생성, 원본은 절대 덮어쓰지 않음)
    --brightness FLOAT  밝기 배율, 1.0=원본, 1.2=20% 밝게, 0.8=20% 어둡게 (기본 1.0)
    --contrast FLOAT    대비 배율, 1.0=원본 (기본 1.0)
    --hue DEGREES        색조 회전(도), -180~180, 0=원본 (기본 0)
    --width INT          최종 가로 크기(px). 하나만 지정하면 비율 유지하며 리사이즈
    --height INT          최종 세로 크기(px)
    --ratio 1:1|4:5|9:16  지정한 비율로 중앙 크롭 (리사이즈보다 먼저 적용)
    --recursive           폴더 입력 시 하위 폴더까지 재귀적으로 처리

예시:
    python edit_photo.py photo.jpg --brightness 1.15 --ratio 1:1 --width 1080
    python edit_photo.py ./photos --ratio 4:5 --out-dir ./photos_insta
"""
import argparse
import os
import sys

from PIL import Image, ImageEnhance

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

RATIO_PRESETS = {
    "1:1": (1, 1),
    "4:5": (4, 5),
    "9:16": (9, 16),
}


def adjust_hue(img, degrees):
    """HSV의 H 채널을 degrees만큼 회전시켜 색조를 바꾼다. 0이면 원본 그대로."""
    if not degrees:
        return img
    had_alpha = img.mode == "RGBA"
    alpha = img.split()[-1] if had_alpha else None
    hsv = img.convert("RGB").convert("HSV")
    h, s, v = hsv.split()
    shift = int(round((degrees % 360) / 360 * 255))
    h = h.point(lambda p: (p + shift) % 256)
    merged = Image.merge("HSV", (h, s, v)).convert("RGB")
    if had_alpha:
        merged.putalpha(alpha)
    return merged


def center_crop_to_ratio(img, ratio_key):
    """지정한 가로:세로 비율에 맞춰 이미지 중앙을 크롭한다."""
    target_w, target_h = RATIO_PRESETS[ratio_key]
    target_ratio = target_w / target_h
    w, h = img.size
    current_ratio = w / h

    if current_ratio > target_ratio:
        # 원본이 더 가로로 넓음 -> 좌우를 잘라낸다
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        box = (left, 0, left + new_w, h)
    else:
        # 원본이 더 세로로 김 -> 위아래를 잘라낸다
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        box = (0, top, w, top + new_h)

    return img.crop(box)


def resize_image(img, width, height):
    if width and height:
        return img.resize((width, height), Image.LANCZOS)
    if width:
        ratio = width / img.width
        return img.resize((width, int(img.height * ratio)), Image.LANCZOS)
    if height:
        ratio = height / img.height
        return img.resize((int(img.width * ratio), height), Image.LANCZOS)
    return img


def process_image(path, args):
    img = Image.open(path)
    original_mode = img.mode
    img = img.convert("RGBA") if "A" in original_mode else img.convert("RGB")

    if args.brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(args.brightness)
    if args.contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(args.contrast)
    if args.hue:
        img = adjust_hue(img, args.hue)
    if args.ratio:
        img = center_crop_to_ratio(img, args.ratio)
    if args.width or args.height:
        img = resize_image(img, args.width, args.height)

    return img


def collect_images(input_path, recursive):
    if os.path.isfile(input_path):
        return [input_path]

    files = []
    if recursive:
        for root, _, names in os.walk(input_path):
            for name in names:
                if os.path.splitext(name)[1].lower() in SUPPORTED_EXT:
                    files.append(os.path.join(root, name))
    else:
        for name in os.listdir(input_path):
            full = os.path.join(input_path, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in SUPPORTED_EXT:
                files.append(full)
    return sorted(files)


def resolve_out_dir(input_path, out_dir):
    if out_dir:
        return out_dir
    base = input_path if os.path.isdir(input_path) else os.path.dirname(os.path.abspath(input_path))
    return os.path.join(base, "edited")


def main():
    parser = argparse.ArgumentParser(description="사진 밝기/대비/색조 보정 + 리사이즈 + 비율 크롭 (Pillow)")
    parser.add_argument("input", help="이미지 파일 또는 이미지가 든 폴더")
    parser.add_argument("--out-dir", help="결과 저장 폴더 (기본: 입력 옆에 edited 폴더 새로 생성)")
    parser.add_argument("--brightness", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--hue", type=float, default=0)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--ratio", choices=list(RATIO_PRESETS.keys()), default=None)
    parser.add_argument("--recursive", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"입력 경로를 찾을 수 없습니다: {args.input}", file=sys.stderr)
        sys.exit(1)

    files = collect_images(args.input, args.recursive)
    if not files:
        print("처리할 이미지 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)

    out_dir = resolve_out_dir(args.input, args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    base_dir = args.input if os.path.isdir(args.input) else os.path.dirname(os.path.abspath(args.input))

    for path in files:
        result = process_image(path, args)
        rel = os.path.relpath(path, base_dir) if os.path.isdir(args.input) else os.path.basename(path)
        out_path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if result.mode == "RGBA" and out_path.lower().endswith((".jpg", ".jpeg")):
            result = result.convert("RGB")
        result.save(out_path)
        print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
