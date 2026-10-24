import os
from pypdf import PdfReader

folder_path = r"datapipline/pastpaperspipline/downlaods"

def pair_qp_and_ms(directory):
  potential_pairs = {}
  paired_list = []
  unpaired_files = []

  files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]

  for file in files:
    file_path = os.path.join(directory, file)
    try:
      reader = PdfReader(file_path)
      meta = reader.metadata
      
      if not meta:
        continue

      doc_type = meta.get('/DocType')
      
      fingerprint = tuple(sorted(
        (k, v) for k, v in meta.items() if k != '/DocType'
      ))

      if fingerprint and doc_type in ['qp', 'ms']:
        if fingerprint not in potential_pairs:
          potential_pairs[fingerprint] = {}
        
        potential_pairs[fingerprint][doc_type] = file

    except Exception:
      continue

  for fingerprint, paths in potential_pairs.items():
    if 'qp' in paths and 'ms' in paths:
      paired_list.append((paths['qp'], paths['ms']))
    else:
      unpaired_files.extend(paths.values())

  return paired_list, unpaired_files

pairs, singles = pair_qp_and_ms(folder_path)

print(f"--- Successfully Paired ({len(pairs)} pairs) ---")
for qp, ms in pairs:
    print(f"QP: {qp} <--> MS: {ms}")
