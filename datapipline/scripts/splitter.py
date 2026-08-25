import os
from pathlib import Path
import re
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter
from langchain_core.documents import Document

base_dir = "datapipline/markdown"
test_file = "test_text_book.pdf"

def split_by_chapters(file_name):
  file_name = Path(file_name).stem + ".md"
  content = Path(os.path.join(base_dir, file_name)).read_text(encoding="utf-8")
  pattern = re.compile(r'^## Chapter.*$', re.M)
  matches = list(pattern.finditer(content))
  for i in range(len(matches)):
    start_pos = matches[i].start()
    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
    chapter_text = content[start_pos:end_pos]
    yield i+1, chapter_text