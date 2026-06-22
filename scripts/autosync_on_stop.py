#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stop hook 用脚本：对话结束时，若【项目状态.md】内容有变更，就推送到飞书。

为什么要这层包装（并发安全设计 —— 用户常同时开多个 Claude 对话）：
  1. 非阻塞文件锁(fcntl flock LOCK_NB)：多个对话同时结束时，只有抢到锁的那个真同步，
     其余瞬间退出，绝不重复写飞书。macOS 没有 flock 命令，所以用 Python fcntl。
  2. 变更检测(md5 比对)：项目状态.md 没变 → 直接跳过，不打扰飞书（天然防刷屏/警报疲劳）。
  3. 绝不碰 git：避免多对话并发撞 .git/index.lock。
  4. 永远 exit 0 + hook 配 async:true：本就后台跑，绝不阻塞对话结束。
  5. 留痕：真同步/出错才写 .claude/autosync.log（跳过不写，免噪音）。
     stdout 打一行状态(SYNCED/SKIP/FAIL/...)仅供手动测试看，hook 后台运行时被忽略。
"""
import os
import sys
import hashlib
import subprocess
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))            # .../Claude Code Projects
STATUS = os.path.join(ROOT, "项目状态.md")
SYNC = os.path.join(ROOT, "AI知识管理系统", "scripts", "sync_projects.py")
STATE = os.path.join(ROOT, ".claude")                    # 整个 .claude/ 已被 gitignore
HASHF = os.path.join(STATE, ".autosync.hash")
LOCKF = os.path.join(STATE, ".autosync.lock")
LOGF = os.path.join(STATE, "autosync.log")


def log(msg):
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def main():
    if not os.path.exists(STATUS):
        print("NOFILE 项目状态.md 不存在")
        return
    os.makedirs(STATE, exist_ok=True)

    import fcntl
    lock_fd = open(LOCKF, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        print("NOLOCK 另一个对话正在同步，跳过")     # 并发：别人在跑，秒退
        return

    try:
        cur = hashlib.md5(open(STATUS, "rb").read()).hexdigest()
        old = ""
        if os.path.exists(HASHF):
            old = open(HASHF).read().strip()
        if cur == old:
            print("SKIP 项目状态.md 未变更")          # 没变：不同步
            return

        r = subprocess.run(
            [sys.executable, SYNC],
            cwd=os.path.dirname(SYNC),
            capture_output=True, text=True, timeout=90,
        )
        if r.returncode == 0:
            with open(HASHF, "w") as f:
                f.write(cur)
            tail = [l for l in r.stdout.splitlines() if "同步完成" in l]
            note = tail[-1].strip() if tail else ""
            log("OK  项目状态.md 变更已同步飞书  " + note)
            print("SYNCED " + note)
        else:
            log("FAIL rc=%s  %s" % (r.returncode, r.stderr.strip()[:200]))
            print("FAIL rc=%s" % r.returncode)
    except subprocess.TimeoutExpired:
        log("TIMEOUT 同步>90s 跳过")
        print("TIMEOUT")
    except Exception as e:
        log("ERROR %s" % e)
        print("ERROR %s" % e)
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except Exception:
            pass


if __name__ == "__main__":
    main()
    sys.exit(0)   # 无论如何不阻塞对话
