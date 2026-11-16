from parse_pdf import process_pdf

maths_structured_qp_path = "datapipline/pastpaperspipline/downlaods/9709_w25_qp_55.pdf"
maths_structured_ms_path = "datapipline/pastpaperspipline/downlaods/9709_w25_ms_55.pdf"
physics_structured_qp_path = "datapipline/pastpaperspipline/downlaods/9702_s26_qp_22.pdf"
physics_structured_ms_path = "datapipline/pastpaperspipline/downlaods/9702_s26_ms_22.pdf"
physics_mcq_qp_path = "datapipline/pastpaperspipline/downlaods/9702_m26_qp_12.pdf"
physics_mcq_ms_path = "datapipline/pastpaperspipline/downlaods/9702_m26_ms_12.pdf"
computer_paper_4_qp_path = "datapipline/pastpaperspipline/downlaods/9618_s26_qp_41.pdf"

process_pdf(computer_paper_4_qp_path, "structured", "qp", 'img', 'scratch', 'questions', False)
# process_pdf(maths_structured_qp_path, "structured", "qp", 'img', 'scratch', 'questions', False)
# process_pdf(maths_structured_ms_path, "structured", "ms", 'img', 'scratch', 'questions', False)
# process_pdf(physics_structured_qp_path, "structured", "qp", 'img', 'scratch', 'questions', False)
# process_pdf(physics_structured_ms_path, "structured", "ms", 'img', 'scratch', 'questions', False)
# process_pdf(physics_mcq_qp_path, "mcq", "qp", 'img', 'scratch', 'questions', False)
# process_pdf(physics_mcq_ms_path, "mcq", "ms", 'img', 'scratch', 'questions', False)