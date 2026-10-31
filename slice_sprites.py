"""
Slices the Shiba puppy sticker sheet into separate PNG files with a transparent background.
Run:  python slice_sprites.py sheet.png
Output: sprites/<name>.png  (cropped, transparent)
"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

SHEET = sys.argv[1] if len(sys.argv) > 1 else "sheet.png"
OUT = "sprites"
os.makedirs(OUT, exist_ok=True)

# (y_start, y_end, number_of_stickers_in_row)  -- 7 rows of stickers
ROWS = [(0, 200, 7), (200, 400, 7), (400, 592, 7), (596, 816, 6),
        (820, 1032, 6), (1036, 1198, 6), (1198, 1403, 7)]

# Name of every sticker, row by row (this is what Robert uses for his moods)
NAMES = [
 ["read1","read2","read_glasses1","read_glasses2","idea","read_lying","read_sleepy"],
 ["chess1","chess2","chess3","chess_happy1","chess_cheer","chess_wink","chess_win"],
 ["hi_big","hi_shy","hi_wave","hi_sit","hi_bubble","hug_heart","happy_blush"],
 ["amazing","special","doing_great","beautiful","incredible","lucky"],
 ["muah","special2","doing_great2","beautiful2","incredible2","lucky2"],
 ["kiss1","kiss2","love_lying","kiss_face","flower","happy_sit"],
 ["cool","coffee","sleep","stay_happy","blanket","flower_crown","heart_bubble"],
]

# sheet-coordinate boxes (x0,y0,x1,y1) of extra bright pixels that belong to a sticker but spill into the next cell
EXTRA = {"hi_big": (120, 395, 250, 470)}

def best_cut(proj, target, window=28):
    lo, hi = max(1, target - window), min(len(proj) - 1, target + window)
    return lo + int(np.argmin(proj[lo:hi]))

img = Image.open(SHEET).convert("RGB")
a = np.array(img).astype(np.int16)
mask = a.max(axis=2) > 30                      # "not black" = sticker

for (y0, y1, n), names in zip(ROWS, NAMES):
    band = mask[y0:y1]
    proj = ndi.uniform_filter1d(band.sum(axis=0).astype(float), 9)
    w = a.shape[1]
    cuts = [0] + [best_cut(proj, int(w * i / n)) for i in range(1, n)] + [w]
    for i, name in enumerate(names):
        x0, x1 = cuts[i], cuts[i + 1]
        cell = mask[y0:y1, x0:x1]
        grown = ndi.binary_dilation(cell, iterations=10)
        lab, k = ndi.label(grown)
        if k == 0:
            continue
        sizes = ndi.sum(grown, lab, range(1, k + 1))
        keep = lab == (1 + int(np.argmax(sizes)))        # biggest blob = the puppy + its hearts
        keep = ndi.binary_dilation(keep, iterations=2) & cell
        keep = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=3))
        # remove tiny pieces touching the cell's left/right edge (bits of the neighbour sticker)
        parts, pk = ndi.label(keep)
        for pi in range(1, pk + 1):
            part = parts == pi
            cols = np.where(part.any(axis=0))[0]
            bluish = (a[y0:y1, x0:x1][part][:, 2].mean() > a[y0:y1, x0:x1][part][:, 0].mean() + 20)
            touches = (cols.min() <= 2 or cols.max() >= part.shape[1] - 3)
            if touches and (bluish or part.sum() < 0.05 * keep.sum()):
                keep[part] = False
        full_keep = np.zeros_like(mask)
        full_keep[y0:y1, x0:x1] = keep
        if name in EXTRA:
            ex0, ey0, ex1, ey1 = EXTRA[name]
            blk = a[ey0:ey1, ex0:ex1]
            white = (blk.min(axis=2) > 190) & ((blk.max(axis=2) - blk.min(axis=2)) < 30)           # the Hiii!! text is white
            full_keep[ey0:ey1, ex0:ex1] |= ndi.binary_dilation(white, iterations=4)
        ys, xs = np.where(full_keep)
        ty0, ty1, tx0, tx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        rgb = np.array(img)[ty0:ty1, tx0:tx1]
        alpha = (full_keep[ty0:ty1, tx0:tx1] * 255).astype(np.uint8)
        # soften the edge so there is no black halo
        alpha = ndi.gaussian_filter(alpha.astype(float), 0.8).astype(np.uint8)
        rgba = np.dstack([rgb, alpha]).astype(np.uint8)
        Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, f"{name}.png"))
print("Done. Sprites saved in:", OUT)

# ---- final clean-up pass: remove stray specks / slivers left from neighbouring stickers ----
KEEP_LARGEST_ONLY = {"stay_happy"}
for fn in os.listdir(OUT):
    if not fn.endswith(".png"):
        continue
    path = os.path.join(OUT, fn)
    im = Image.open(path).convert("RGBA")
    arr = np.array(im)
    solid = arr[..., 3] > 128
    parts, pk = ndi.label(solid)
    if pk == 0:
        continue
    areas = ndi.sum(solid, parts, range(1, pk + 1))
    biggest = 1 + int(np.argmax(areas))
    for pi in range(1, pk + 1):
        drop = areas[pi - 1] < 80 or (fn[:-4] in KEEP_LARGEST_ONLY and pi != biggest)
        if drop:
            arr[ndi.binary_dilation(parts == pi, iterations=3), 3] = 0
    ys, xs = np.where(arr[..., 3] > 0)
    Image.fromarray(arr[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA").save(path)
print("Clean-up done.")
