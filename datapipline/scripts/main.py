from chunking import chunk_chapter
from splitter import split_by_chapters

base_dir = "datapipline/markdown"
test_file = "test_text_book.pdf"
count_chapter = 3
counter = 0

for chapter_num, chapter_text in split_by_chapters(test_file, base_dir):
  if counter < count_chapter:
    chunks = chunk_chapter(chapter_num=chapter_num, chapter_text=chapter_text, source_file=test_file)
  else:
    break
  counter += 1

print(f"chunks extracted from chapter: {chunks[0].metadata["chapter_title"]}")
print(f"number of chunks {len(chunks)}")
for chunk in chunks:
  print(f"{chunk.metadata} \n\n")