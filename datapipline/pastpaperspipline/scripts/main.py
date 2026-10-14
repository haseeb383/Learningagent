from dataprep.extract_lines import extract_lines
from coordsfinding.qp_parser import parse_qp
from coordsfinding.parse_ms import parse_ms
from chunking.chunker import create_chunks
import json

# maths_structured_qp_path = "datapipline/pastpaperspipline/downlaods/9709_w25_qp_55.pdf"
# maths_structured_qp_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9709_w25_qp_55.pdf")
# parse_qp(maths_structured_qp_lines)
# with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
#     maths_structured_qp_coords = json.load(file)
# create_chunks(pdf_path=maths_structured_qp_path, coords=maths_structured_qp_coords)

# maths_structured_ms_path = "datapipline/pastpaperspipline/downlaods/9709_w25_ms_55.pdf"
# maths_structured_ms_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9709_w25_ms_55.pdf")
# parse_ms(maths_structured_ms_lines)
# with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
#     maths_structured_ms_coords = json.load(file)
# create_chunks(pdf_path=maths_structured_ms_path, coords=maths_structured_ms_coords)

physics_structured_qp_path = "datapipline/pastpaperspipline/downlaods/9702_s26_qp_22.pdf"
physics_structured_qp_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_s26_qp_22.pdf")
parse_qp(physics_structured_qp_lines)
with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
    physics_structured_qp_coords = json.load(file)
create_chunks(pdf_path=physics_structured_qp_path, coords=physics_structured_qp_coords)

# physics_structured_ms_path = "datapipline/pastpaperspipline/downlaods/9702_s26_ms_22.pdf"
# physics_structured_ms_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_s26_ms_22.pdf")
# parse_ms(physics_structured_ms_lines)
# with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
#     physics_structured_ms_coords = json.load(file)
# create_chunks(pdf_path=physics_structured_ms_path, coords=physics_structured_ms_coords)

# physics_mcq_qp_path = "datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf"
# physics_mcq_qp_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf")
# parse_qp(physics_mcq_qp_lines)
# with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
#     physics_mcq_qp_coords = json.load(file)
# create_chunks(pdf_path=physics_mcq_qp_path, coords=physics_mcq_qp_coords)

# physics_mcq_ms_path = "datapipline/pastpaperspipline/downlaods/9702_m26_ms_12.pdf"
# physics_mcq_ms_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_m26_ms_12.pdf")
# parse_ms(physics_mcq_ms_lines, question_type="mcq")
# with open('datapipline/pastpaperspipline/coords/qp_coords.json', 'r') as file:
#     physics_mcq_ms_coords = json.load(file)
# create_chunks(pdf_path=physics_mcq_ms_path, coords=physics_mcq_ms_coords)
