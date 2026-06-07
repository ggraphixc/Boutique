"""
Apply consistent dark-mode Tailwind variants to all admin section templates.
Maps the most common light-only class patterns to their dark equivalents.
"""
import re
from pathlib import Path

REPLACEMENTS = [
    # Backgrounds
    (r'\bbg-white\b(?! dark:)', 'bg-white dark:bg-[#111114]'),
    (r'\bbg-\[#FAFAFA\]\b(?! dark:)', 'bg-[#FAFAFA] dark:bg-[#0B0B0D]'),
    (r'\bbg-gray-50\b(?! dark:)', 'bg-gray-50 dark:bg-[#18181B]'),
    (r'\bbg-gray-100\b(?! dark:)', 'bg-gray-100 dark:bg-[#27272A]'),

    # Borders
    (r'\bborder-gray-100\b(?! dark:)', 'border-gray-100 dark:border-gray-800'),
    (r'\bborder-gray-200\b(?! dark:)', 'border-gray-200 dark:border-gray-800'),
    (r'\bborder-gray-300\b(?! dark:)', 'border-gray-300 dark:border-gray-700'),
    (r'\bdivide-gray-100\b(?! dark:)', 'divide-gray-100 dark:divide-gray-800'),
    (r'\bdivide-gray-200\b(?! dark:)', 'divide-gray-200 dark:divide-gray-800'),

    # Text
    (r'\btext-gray-900\b(?! dark:)', 'text-gray-900 dark:text-gray-100'),
    (r'\btext-gray-800\b(?! dark:)', 'text-gray-800 dark:text-gray-200'),
    (r'\btext-gray-700\b(?! dark:)', 'text-gray-700 dark:text-gray-200'),
    (r'\btext-gray-600\b(?! dark:)', 'text-gray-600 dark:text-gray-300'),
    (r'\btext-gray-500\b(?! dark:)', 'text-gray-500 dark:text-gray-400'),
    (r'\btext-gray-400\b(?! dark:)', 'text-gray-400 dark:text-gray-500'),

    # Hovers
    (r'\bhover:bg-gray-50\b(?! dark:)', 'hover:bg-gray-50 dark:hover:bg-[#18181B]'),
    (r'\bhover:bg-gray-100\b(?! dark:)', 'hover:bg-gray-100 dark:hover:bg-[#27272A]'),
    (r'\bhover:text-gray-900\b(?! dark:)', 'hover:text-gray-900 dark:hover:text-gray-100'),

    # Rings / shadows
    (r'\bring-gray-200\b(?! dark:)', 'ring-gray-200 dark:ring-gray-700'),
]


def patch_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for pat, sub in REPLACEMENTS:
        new, count = re.subn(pat, sub, text)
        if count:
            text = new
            n += count
    if n:
        path.write_text(text, encoding="utf-8")
    return n


if __name__ == "__main__":
    sections_dir = Path("app/templates/admin/sections")
    for f in sorted(sections_dir.glob("*.html")):
        c = patch_file(f)
        print(f"{f.name}: {c} replacements")
