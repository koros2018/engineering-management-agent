#!/usr/bin/env python3
"""
DWG → DXF 批量转换脚本 (libredwg 原生二进制)
用法: python3 dwg_to_dxf_batch.py <input_dir> <output_dir> [--dwg2dxf /path/to/dwg2dxf]

依赖: libredwg 编译后的 dwg2dxf 二进制
编译方法:
  wget https://ftp.gnu.org/gnu/libredwg/libredwg-0.13.3.tar.xz
  tar xf libredwg-0.13.3.tar.xz && cd libredwg-0.13.3
  ./configure && make -j$(nproc)
  # 二进制在 programs/dwg2dxf
"""
import os
import sys
import subprocess
import json
import time
from pathlib import Path

DEFAULT_DWG2DXF = "/tmp/libredwg-0.13.3/programs/dwg2dxf"

def find_dwg2dxf():
    """查找 dwg2dxf 二进制"""
    # 1. 环境变量
    env_path = os.environ.get("DWG2DXF")
    if env_path and os.path.isfile(env_path):
        return env_path
    # 2. 默认路径
    if os.path.isfile(DEFAULT_DWG2DXF):
        return DEFAULT_DWG2DXF
    # 3. PATH 中查找
    for p in os.environ.get("PATH", "").split(":"):
        candidate = os.path.join(p, "dwg2dxf")
        if os.path.isfile(candidate):
            return candidate
    return None

def convert_file(dwg_path, out_path, dwg2dxf):
    """转换单个 DWG → DXF"""
    start = time.time()
    result = subprocess.run(
        [dwg2dxf, "-o", str(out_path), str(dwg_path)],
        capture_output=True, text=True, timeout=300
    )
    elapsed = time.time() - start
    success = result.returncode == 0 and os.path.isfile(out_path)
    size = os.path.getsize(out_path) if success else 0
    return {
        "success": success,
        "elapsed_ms": round(elapsed * 1000),
        "size": size,
        "stderr": result.stderr[:200] if not success else ""
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="DWG → DXF 批量转换")
    parser.add_argument("input_dir", help="输入目录 (包含 .dwg 文件)")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--dwg2dxf", default=None, help="dwg2dxf 二进制路径")
    parser.add_argument("--skip-existing", action="store_true", default=True,
                        help="跳过已存在的 DXF 文件 (默认 True)")
    parser.add_argument("--min-size", type=int, default=10240,
                        help="跳过大于此字节的已有 DXF (默认 10KB)")
    args = parser.parse_args()

    dwg2dxf = args.dwg2dxf or find_dwg2dxf()
    if not dwg2dxf:
        print("❌ 找不到 dwg2dxf 二进制。请编译 libredwg 或指定 --dwg2dxf 路径")
        print(f"   默认查找: {DEFAULT_DWG2DXF}")
        sys.exit(1)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dwg_files = sorted(input_dir.glob("*.dwg"))
    if not dwg_files:
        print(f"❌ {input_dir} 中没有 .dwg 文件")
        sys.exit(1)

    print(f"🔧 dwg2dxf: {dwg2dxf}")
    print(f"📁 输入: {input_dir}")
    print(f"📁 输出: {output_dir}")
    print(f"📄 待转换: {len(dwg_files)} 个 DWG 文件\n")

    results = []
    ok = skip = fail = 0

    for dwg in dwg_files:
        name = dwg.stem
        out = output_dir / f"{name}.dxf"

        if args.skip_existing and out.exists() and out.stat().st_size > args.min_size:
            print(f"⏭️  跳过: {name} ({out.stat().st_size // 1024}KB)")
            skip += 1
            results.append({"file": str(dwg), "status": "skipped"})
            continue

        print(f"🔄 转换: {dwg.name} ({dwg.stat().st_size / 1024 / 1024:.1f}MB)")
        r = convert_file(dwg, out, dwg2dxf)

        if r["success"]:
            print(f"  ✅ 成功 → {name}.dxf ({r['size'] // 1024}KB, {r['elapsed_ms']}ms)")
            ok += 1
            results.append({"file": str(dwg), "status": "ok", **r})
        else:
            print(f"  ❌ 失败: {name}")
            if r["stderr"]:
                print(f"     {r['stderr']}")
            fail += 1
            results.append({"file": str(dwg), "status": "failed", **r})

    print(f"\n{'='*50}")
    print(f"成功: {ok}, 跳过: {skip}, 失败: {fail}")
    print(f"总计: {len(dwg_files)}")

    # 保存报告
    report_path = output_dir / "conversion_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"报告: {report_path}")

if __name__ == "__main__":
    main()
