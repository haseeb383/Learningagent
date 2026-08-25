import os
import shutil
from pathlib import Path
import re

base_dir = "datapipline/markdown"
test_file = "test_text_book.pdf"

def _check_for_copy(file_name):
  file_name = Path(file_name).stem + ".md"
  file = Path(file_name).stem
  copy_file_name = file + "_copy.md"
  if not os.path.isfile(os.path.join(base_dir, copy_file_name)):
    shutil.copy2(os.path.join(base_dir, file_name), os.path.join(base_dir, copy_file_name))
    return copy_file_name
  elif os.path.isfile(os.path.join(base_dir, file + "_copy.md")):
    return copy_file_name

def _split_chapter(file_name):
  file_name = _check_for_copy(file_name)


def _recursive_chunking(chapter):
  pass

def split_chunk(input_file):
  pass

_check_for_copy(test_file)