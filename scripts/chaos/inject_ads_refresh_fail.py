#!/usr/bin/env python3
"""
混沌场景 4：ADS 刷新失败（对齐 EcomAI §14.4）

优先：POST /admin/chaos/ads-refresh-fail
回退：打印 EcomAI 侧需开启的 feature flag 说明（ADS_REFRESH_CHAOS=1）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from _config import ScriptConfig
from chaos._common import log, patch_env_value, resolve_ecom_env_file, restore_env_value, try_chaos_api, wait_with_countdown


def main() -> int:
    parser = argparse.ArgumentParser(description="注入 ADS 刷新失败混沌")
    parser.add_argument("--duration", type=int, default=300, help="混沌持续秒数")
    parser.add_argument("--disable", action="store_true", help="关闭混沌")
    parser.add_argument("--force-env", action="store_true", help="改 EcomAI .env ADS_REFRESH_CHAOS")
    args = parser.parse_args()

    config = ScriptConfig.load()
    enable = not args.disable

    if not args.force_env:
        ok = try_chaos_api(
            config,
            path="/admin/chaos/ads-refresh-fail",
            payload={"enable": enable, "duration_seconds": args.duration},
        )
        if ok:
            if enable:
                wait_with_countdown(args.duration, "ADS 刷新失败混沌已开启")
                try_chaos_api(config, path="/admin/chaos/ads-refresh-fail", payload={"enable": False})
            return 0
        log("未命中 EcomAI chaos API")

    env_path = resolve_ecom_env_file(config)
    if env_path is None:
        log("请在 EcomAI Admin 开启 ADS 刷新失败演示开关，或实现 POST /admin/chaos/ads-refresh-fail")
        log("预期现象：定时 ADS 任务失败日志 + admin 侧 medium 级告警（造数阶段可用 AdsRefreshFailed）")
        return 1

    value = "1" if enable else "0"
    old = patch_env_value(env_path, "ADS_REFRESH_CHAOS", value)
    log(f"已设置 {env_path} ADS_REFRESH_CHAOS={value}（原值={old}）")
    log("请重启 ecom-api Admin 进程，并手动触发一次 ADS 刷新任务")
    if enable:
        wait_with_countdown(args.duration, "等待 ADS 混沌窗口")
        restore_env_value(env_path, "ADS_REFRESH_CHAOS", old)
        log("已还原 ADS_REFRESH_CHAOS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
