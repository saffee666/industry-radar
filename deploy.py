#!/usr/bin/env python3
"""部署脚本：上传修改文件到阿里云服务器并验证"""
import paramiko
import os
from pathlib import Path

HOST = "47.109.136.188"
USER = "root"
PASS = "Xiachunhao689,123"
REMOTE_BASE = "/root/industry-radar"
LOCAL_BASE = Path(__file__).parent

FILES = [
    "collectors/tech_communities.py",
    "collectors/job_markets.py",
    "collectors/freelance_markets.py",
    "collectors/chinese_platforms.py",
    "collectors/policy_media.py",
    "collectors/cookie_loader.py",
    "config/cookies.json",
    "config/industries.yaml",
    "processors/classifier.py",
    "processors/scorer.py",
    "reports/morning_brief.py",
    "collect_and_report.py",
]


def ssh_cmd(client, cmd, timeout=120):
    """执行远程命令并打印输出"""
    print(f"  $ {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out:
        print(out[:500])
    if err:
        print(f"  STDERR: {err[:200]}")
    return out, err


def main():
    print(f"=== 连接 {USER}@{HOST} ===\n")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(HOST, username=USER, password=PASS, timeout=15)
    except Exception as e:
        print(f"连接失败: {e}")
        return

    print("已连接\n")

    # 检查远程环境
    print("--- 服务器环境 ---")
    ssh_cmd(client, "python3 --version && pip3 list 2>/dev/null | grep -iE 'requests|yaml|jieba'")
    ssh_cmd(client, f"ls {REMOTE_BASE}/collectors/ 2>/dev/null || echo '目录不存在'")

    # 上传文件
    print("\n--- 上传文件 ---")
    sftp = client.open_sftp()
    for rel_path in FILES:
        local = LOCAL_BASE / rel_path
        remote = f"{REMOTE_BASE}/{rel_path}"
        if local.exists():
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                sftp.mkdir(remote_dir)
            sftp.put(str(local), remote)
            print(f"  OK: {rel_path}")
        else:
            print(f"  MISS: {local}")
    sftp.close()

    # 创建日志目录
    ssh_cmd(client, f"mkdir -p {REMOTE_BASE}/output/logs")

    # 运行验证
    print("\n--- 运行采集验证 ---")
    ssh_cmd(client, f"cd {REMOTE_BASE} && python3 collect_and_report.py 2>&1", timeout=300)

    # 显示最新结果
    print("\n--- 最新晨报 ---")
    ssh_cmd(client, f"ls -la {REMOTE_BASE}/output/briefs/ | tail -5")

    client.close()
    print("\n=== 部署完成 ===")


if __name__ == "__main__":
    main()
