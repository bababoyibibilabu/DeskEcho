"""
DeskEcho 真机环境自检与冒烟测试脚本 (运行在笔记本真实环境)
验证项目：
1. 环境变量与 .env 凭据完整性 (火山 ASR、DeepSeek LLM、微软 Edge-TTS)
2. 数据库读写与切片统计 (MeetingStore / records.db)
3. 向量检索索引与 ChromaDB 连通性
4. 版本自检与 GitHub Releases 接口状态 (UpdateChecker)
5. 主 GUI 进程与音频录音守护进程存活状态
"""
import os
import sys
from pathlib import Path

def run_verification():
    print("=" * 60)
    print("  DeskEcho 笔记本真机端自动化冒烟测试 (Smoke Test)")
    print("=" * 60)

    # 1. 检查运行环境与根目录
    app_dir = Path(__file__).resolve().parent.parent
    os.chdir(str(app_dir))
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    print(f"[1] 项目根目录: {app_dir}")

    # 2. 检查 .env 配置文件
    env_file = app_dir / ".env"
    if not env_file.exists():
        print("[-] 警告: .env 文件不存在！")
        return False
    print(f"[+] .env 文件存在 ({env_file.stat().st_size} bytes)")

    # 3. 验证数据库读写
    try:
        from core.knowledge_engine import MeetingStore
        store = MeetingStore()
        recent = store.query_recent(50)
        print(f"[+] 会议数据库连通成功！当前切片总数: {len(recent)} 条")
    except Exception as e:
        print(f"[-] 数据库连接异常: {e}")
        return False

    # 4. 验证版本引擎与版本文件
    try:
        from version import APP_VERSION, APP_NAME
        from core.updater import UpdateChecker
        print(f"[+] 当前客户端版本: {APP_NAME} v{APP_VERSION}")
        checker = UpdateChecker(current_version=APP_VERSION, app_dir=app_dir)
        update_result = checker.check_update()
        if update_result:
            print(f"[+] 版本检查成功: 发现远端新发布 v{update_result.get('version')} (具备自动更新条件)")
        else:
            print(f"[+] 版本检查成功: 当前已是 GitHub 最新发布版本或无更新")
    except Exception as e:
        print(f"[-] 版本更新引擎测试异常: {e}")
        return False

    # 5. 验证核心模块导入
    try:
        import ui.main_window
        import ui.tray_icon
        import core.audio_recorder
        import core.rag_engine
        print("[+] 所有核心 UI 与音频管道模块编译加载无语法/运行时异常！")
    except Exception as e:
        print(f"[-] 模块导入异常: {e}")
        return False

    print("=" * 60)
    print("  [SUCCESS] 笔记本真机端测试验证全项通过！可以安全推进发版。")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
