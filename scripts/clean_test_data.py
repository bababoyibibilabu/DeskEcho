import sqlite3
from pathlib import Path
import json

db_locations = [
    Path("C:/DeskEcho/omni_data/records.db"),
    Path("D:/DeskEcho_Data/records.db"),
    Path("./omni_data/records.db"),
    Path("D:/DeskEcho_Data"),
]

def search_and_clean():
    found_any = False
    for p in [
        Path("C:/DeskEcho/omni_data/records.db"),
        Path("D:/DeskEcho_Data/records.db"),
        Path("./omni_data/records.db"),
    ]:
        if not p.exists():
            continue
        print(f"Checking database at: {p}")
        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # 1. 查找包含“布鞋”或“老北京”或明显测试生成的会议切片
        cur.execute("SELECT id, start_time, end_time, summary, raw_text FROM meeting_slices")
        rows = cur.fetchall()
        print(f"Total slices in {p}: {len(rows)}")
        delete_ids = []
        for r in rows:
            summary = r["summary"] or ""
            raw_text = r["raw_text"] or ""
            content = summary + " " + raw_text
            if "布鞋" in content or "老北京" in content or "测试切片" in content or "测试数据" in content:
                print(f"  [Found Test Slice] ID={r['id']}, Summary={summary[:60]}")
                delete_ids.append(r["id"])
                found_any = True
                
        if delete_ids:
            cur.executemany("DELETE FROM meeting_slices WHERE id = ?", [(did,) for did in delete_ids])
            conn.commit()
            print(f"  [Deleted] {len(delete_ids)} test slices from {p}")
            
            # 同时从 chroma 中删除
            chroma_dir = p.parent / "chroma"
            if chroma_dir.exists():
                try:
                    import chromadb
                    client = chromadb.PersistentClient(path=str(chroma_dir))
                    coll = client.get_collection("meeting_memories")
                    coll.delete(ids=delete_ids)
                    print(f"  [Deleted from Chroma] {len(delete_ids)} embeddings")
                except Exception as e:
                    print(f"  [Chroma Delete Warning] {e}")
                    
        # 2. 检查会话记录 (chat_turns / chat_sessions)
        try:
            cur.execute("SELECT id, query, answer FROM chat_turns")
            t_rows = cur.fetchall()
            del_turns = []
            for tr in t_rows:
                q = tr["query"] or ""
                a = tr["answer"] or ""
                if "布鞋" in (q + a) or "老北京" in (q + a):
                    print(f"  [Found Test Turn] ID={tr['id']}, Query={q}")
                    del_turns.append(tr["id"])
            if del_turns:
                cur.executemany("DELETE FROM chat_turns WHERE id = ?", [(tid,) for tid in del_turns])
                conn.commit()
                print(f"  [Deleted] {len(del_turns)} test turns from {p}")
        except Exception as e:
            pass
            
        conn.close()

if __name__ == "__main__":
    search_and_clean()
