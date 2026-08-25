import os
from pathlib import Path
import re

base_dir = "datapipline/markdown"
test_file = "test_text_book.pdf"

def _split_chapter(file_name):
  file_name = Path(file_name).stem + ".md"
  content = os.path.join(base_dir, file_name).read_text(encoding="utf-8")
  pattern = re.compile(r'^## Chapter.*$', re.M)
  matches = list(pattern.finditer(content))
  for i in range(len(matches)):
    start_pos = matches[i].start()
    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
    chapter_text = content[start_pos:end_pos]
    yield i+1, chapter_text