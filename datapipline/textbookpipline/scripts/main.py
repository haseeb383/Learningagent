from datapipline.textbookpipline.scripts.chunking import chunk_chapter
from datapipline.textbookpipline.scripts.splitter import split_by_chapters
from datapipline.textbookpipline.scripts.embedding_store import embedding_model, store_chunks

base_dir = "datapipline/markdown"
test_file = "test_text_book.pdf"
count_chapter = 1
counter = 0
def basic_data_pipline():
  for chapter_num, chapter_text in split_by_chapters(test_file, base_dir):
    chunks = chunk_chapter(chapter_num=chapter_num, chapter_text=chapter_text, source_file=test_file)
    store_chunks(chunks, embedding_model)

def test_chunking(count_chapter, counter):
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

# test_chunking(count_chapter, counter)
basic_data_pipline()