import os
from pypdf import PdfReader

# Set the path to your single folder containing all PDFs
folder_path = r"datapipline/pastpaperspipline/downlaods"

def pair_qp_and_ms(directory):
    # Dictionary structure: { (metadata_fingerprint): {"qp": filename, "ms": filename} }
    potential_pairs = {}
    paired_list = []
    unpaired_files = []

    # Get all PDF files in the directory
    files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]

    for file in files:
        file_path = os.path.join(directory, file)
        try:
            reader = PdfReader(file_path)
            meta = reader.metadata
            
            if not meta:
                continue

            # Extract DocType and remove it to create a matching fingerprint
            doc_type = meta.get('/DocType')
            
            # Create a frozen/immutable copy of metadata items excluding DocType
            fingerprint = tuple(sorted(
                (k, v) for k, v in meta.items() if k != '/DocType'
            ))

            # Only process if it has a valid fingerprint and a DocType of qp or ms
            if fingerprint and doc_type in ['qp', 'ms']:
                if fingerprint not in potential_pairs:
                    potential_pairs[fingerprint] = {}
                
                # Store the filename (base name) instead of full file_path
                potential_pairs[fingerprint][doc_type] = file
                
        except Exception:
            # Skip corrupted or unreadable PDFs
            continue

    # Build the final list of tuples
    for fingerprint, paths in potential_pairs.items():
        if 'qp' in paths and 'ms' in paths:
            # Found a perfect match, append as (qp_filename, ms_filename)
            paired_list.append((paths['qp'], paths['ms']))
        else:
            # Keep track of files that didn't find a partner
            unpaired_files.extend(paths.values())

    return paired_list, unpaired_files

pairs, singles = pair_qp_and_ms(folder_path)

# Print results
print(f"--- Successfully Paired ({len(pairs)} pairs) ---")
for qp, ms in pairs:
    print(f"QP: {qp} <--> MS: {ms}")

if singles:
    print(f"\n--- Unpaired Files ({len(singles)}) ---")
    for file in singles:
        print(f"Missing Partner: {os.path.basename(file)}")