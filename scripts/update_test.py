from pathlib import Path

p = Path("scripts/test_memory_hierarchy_cleanup.py")
text = p.read_text(encoding="utf-8")
old = '"会议记忆库 (30)"'
new = '"会议记忆库"'
text = text.replace(old, new)
p.write_text(text, encoding="utf-8")
print("Updated test script!")
