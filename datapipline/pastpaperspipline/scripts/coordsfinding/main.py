from parse_qp_structured import find_structured_qp_coords
from parse_ms import find_ms_coords
from extract_lines import extract_lines


qp_structured_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9709_w25_qp_55.pdf")
qp_mcq_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf")
ms_structured_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9709_w25_ms_55.pdf")
ms_mcq_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_m26_ms_12.pdf")


test_lines = extract_lines("datapipline/pastpaperspipline/downlaods/9702_s26_qp_22.pdf")
with open("lines.txt", "w") as file:
  file.write(test_lines)
print("saved in lines.txt")