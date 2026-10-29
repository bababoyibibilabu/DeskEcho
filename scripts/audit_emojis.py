import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

pattern = re.compile(r'[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]')

print("Auditing all files under ui/ and core/...")
count = 0
for d in ['ui', 'core']:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.py') and f != 'icons.py':
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as fp:
                    for idx, line in enumerate(fp, 1):
                        found = pattern.findall(line)
                        if found:
                            has_real_emo = any(ord(c) not in (0x2713, 0x2715) for c in found)
                            if has_real_emo and not ('re.sub' in line or 'r\'' in line or 'r"' in line or 'for emo in' in line or line.strip().startswith('#') or line.strip().startswith('*') or line.strip().startswith('-')):
                                count += 1
                                print(f"{path}:{idx}: {''.join(set(found))} -> {line.strip()[:80]}")

print(f"\nTotal non-docstring emoji occurrences: {count}")
