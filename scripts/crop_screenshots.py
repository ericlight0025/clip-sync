"""
裁切 docs/screenshots/ 裡的截圖
- 自動偵測左側白邊並裁掉
- 裁切底部空白（保留到 90% 高度附近的最後一個非空白列）
"""
from pathlib import Path
from PIL import Image

SCREENSHOT_DIR = Path(__file__).parent.parent / "docs" / "screenshots"
SUFFIXES = [".png", ".jpg"]

def find_left_crop(img):
    """找左側白邊結束的 x 座標（RGB 三個 channel 平均 > 240 就當白邊）"""
    width, height = img.size
    sample_rows = [height // 4, height // 2, height * 3 // 4]
    for x in range(width):
        for y in sample_rows:
            r, g, b = img.getpixel((x, y))[:3]
            if (r + g + b) / 3 < 230:
                return max(0, x - 2)
    return 0

def find_bottom_crop(img, left):
    """找底部最後一個有內容的 y 座標（掃描左側 sidebar 寬度範圍）"""
    width, height = img.size
    sidebar_right = left + int((width - left) * 0.22)  # sidebar 約佔 22% 寬

    last_content_y = height
    for y in range(height - 1, height // 2, -1):
        found = False
        for x in range(left, sidebar_right, 4):
            r, g, b = img.getpixel((x, y))[:3]
            if (r + g + b) / 3 > 50:  # 不是純黑就算有內容
                found = True
                break
        if found:
            last_content_y = y + 20  # 留一點 padding
            break

    return min(last_content_y, height)

for path in sorted(SCREENSHOT_DIR.iterdir()):
    if path.suffix.lower() not in SUFFIXES:
        continue

    img = Image.open(path).convert("RGB")
    w, h = img.size
    print(f"\n{path.name}: 原始 {w}x{h}")

    left = find_left_crop(img)
    bottom = find_bottom_crop(img, left)

    cropped = img.crop((left, 0, w, bottom))
    cropped.save(path)
    cw, ch = cropped.size
    print(f"  → 裁切後 {cw}x{ch}  (左裁 {left}px, 底部裁 {h - bottom}px)")

print("\n完成。")
