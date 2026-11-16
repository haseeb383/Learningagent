from extract_lines import extract_lines
from parse_qp import parse_qp
from parse_ms import parse_ms
from chunker import create_chunks_from_scratch
import json
from pathlib import Path

def process_pdf(pdf_path, question_type="structured", doc_type="qp", chunk_type='img', chunk_from='scratch', coord_type='all', include_subparts=False):
	lines = extract_lines(pdf_path=pdf_path)
	pdf_name = Path(pdf_path).stem
	if chunk_from == 'scratch':
		if doc_type == 'qp':
			parse_qp(lines, pdf_path, question_type, coord_type, include_subparts)
			with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
				coords = json.load(file)
		elif doc_type == 'ms':
			parse_ms(pdf_path, lines, question_type)
			with open('datapipline/pastpaperspipline/coords/ms_coords.json', 'r') as file:
				coords = json.load(file)
		create_chunks_from_scratch(pdf_path, coords, chunk_type, question_type, doc_type)
	elif chunk_from == 'coords':
		coords_file_path = 'datapipline/pastpaperspipline/coords/' + pdf_name + ".json"
		with open(coords_file_path, 'r') as file:
			coords = json.load(file)
		create_chunks_from_scratch(pdf_path, coords, chunk_type, question_type, doc_type)