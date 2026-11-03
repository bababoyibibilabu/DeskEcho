from pathlib import Path

p = Path("ui/main_window.py")
text = p.read_text(encoding="utf-8")
old = 'self.sub_btn_memory.setText(f"会议记忆库 ({len(normal_recs)})")'
new = 'self.sub_btn_memory.setText("会议记忆库")'
if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("Successfully replaced!")
else:
    print("Warning: old text not found")
