"""Run:  python check_sheet.py   - shows if Robert's picture sheet matches the settings."""
from PIL import Image
import config

im = Image.open(config.SPRITE_SHEET)
w, h = im.size
print("Sheet size:", w, "x", h)
print("Settings say:", config.SHEET_COLUMNS, "columns and", config.SHEET_ROWS, "rows")
print("So each picture will be:", w // config.SHEET_COLUMNS, "x", h // config.SHEET_ROWS)
print()
print("With the cleaned sheet I gave you, it MUST say:  640 x 801  and  80 x 89")
