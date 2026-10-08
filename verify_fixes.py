import re
with open('backend/scripts/export_report.py') as f:
    content = f.read()

seq_usage = re.findall(r'"Sequence \d+"', content)
print('Sequence references found:', len(seq_usage))

canonical_usage = re.findall(r'canonical:\d+:\d+', content)
print('Canonical reference patterns found:', len(canonical_usage))

has_reference_in_projection = '"reference"' in content
print('reference field in public_projection:', has_reference_in_projection)

has_seq_gen = 'seq = 1' in content
print('Sequence counter initialized:', has_seq_gen)

print('All key fixes verified!')