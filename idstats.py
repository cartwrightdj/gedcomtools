import re
from collections import defaultdict
from typing import Dict, List

PATTERN = re.compile(r'#(?!\s)([^"]*?)"')

def natural_key(s: str):
    import re as _re
    return [int(t) if t.isdigit() else t.lower() for t in _re.split(r'(\d+)', s)]

def find_hash_quotes(filename: str) -> Dict[str, Dict[str, List[int]]]:
    hits: Dict[str, Dict[str, set]] = defaultdict(lambda: {'count': 0, 'lines': set()})
    with open(filename, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, start=1):
            for captured in PATTERN.findall(line):
                if captured:
                    hits[captured]['count'] += 1
                    hits[captured]['lines'].add(lineno)
    return {k: {'count': v['count'], 'lines': sorted(v['lines'])} for k, v in hits.items()}

def categorize_hits(hits: Dict[str, Dict[str, List[int]]]):
    buckets = defaultdict(dict)
    for ident, data in hits.items():
        first = ident[0].upper() if ident else ''
        cat = first if first.isalpha() else 'OTHER'
        buckets[cat][ident] = data
    return buckets

def print_grouped_table(buckets):
    # Column widths (don't base on full lines string, just a reasonable limit)
    all_ids = [('#' + ident) for bucket in buckets.values() for ident in bucket.keys()]
    key_width = max((len(k) for k in all_ids), default=6)
    count_width = max((len(str(data['count'])) for bucket in buckets.values() for data in bucket.values()), default=5)

    categories = sorted([c for c in buckets.keys() if c != 'OTHER']) + (['OTHER'] if 'OTHER' in buckets else [])

    for cat in categories:
        bucket = buckets[cat]
        if not bucket:
            continue

        print(f"\n[{cat}]")
        print(f"{'STRING':<{key_width}}  {'COUNT':>{count_width}}  LINES")
        print(f"{'-'*key_width}  {'-'*count_width}  {'-'*5}")

        for ident in sorted(bucket.keys(), key=natural_key):
            data = bucket[ident]
            lines_str = ','.join(map(str, data['lines']))
            # wrap long lines lists at ~60 chars
            wrap_limit = 60
            if len(lines_str) <= wrap_limit:
                print(f"{('#' + ident):<{key_width}}  {data['count']:>{count_width}}  {lines_str}")
            else:
                # first line
                print(f"{('#' + ident):<{key_width}}  {data['count']:>{count_width}}  {lines_str[:wrap_limit]}")
                # wrapped continuation lines
                for i in range(wrap_limit, len(lines_str), wrap_limit):
                    print(f"{'':<{key_width}}  {'':>{count_width}}  {lines_str[i:i+wrap_limit]}")

def main():
    filename = 'persons.json'
    hits = find_hash_quotes(filename)
    if not hits:
        print("No matches found.")
        return
    buckets = categorize_hits(hits)
    print_grouped_table(buckets)

if __name__ == "__main__":
    main()
