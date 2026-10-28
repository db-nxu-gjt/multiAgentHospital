"""
打包脚本 - 一键构建医院虚拟会诊系统可执行程序

用法：
    python scripts/build_exe.py

或在项目根目录直接调用 PyInstaller：
    pyinstaller build.spec --clean --noconfirm

产物路径：
    dist/医院虚拟会诊系统/医院虚拟会诊系统.exe
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    print("=" * 60)
    print("医院虚拟会诊系统 - 打包构建")
    print("=" * 60)

    # 1. 检查 PyInstaller
    try:
        import PyInstaller  # noqa
        print(f"✓ PyInstaller 已安装: {PyInstaller.__version__}")
    except ImportError:
        print("✗ 未检测到 PyInstaller，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])

    # 2. 清理旧产物
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    if build_dir.exists():
        print(f"✓ 清理旧 build 目录: {build_dir}")
        shutil.rmtree(build_dir, ignore_errors=True)
    if dist_dir.exists():
        print(f"✓ 清理旧 dist 目录: {dist_dir}")
        shutil.rmtree(dist_dir, ignore_errors=True)

    # 3. 确保 data 目录存在（防止打包空目录）
    data_dir = project_root / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        print(f"✓ 创建 data 目录: {data_dir}")

    # 4. 运行测试（可选但推荐）
    run_tests = os.environ.get("VCS_SKIP_TESTS", "0") != "1"
    if run_tests:
        print("\n[1/3] 运行测试套件...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
                cwd=str(project_root)
            )
            print("✓ 测试全部通过")
        except subprocess.CalledProcessError as e:
            print(f"✗ 测试失败（返回码 {e.returncode}），请先修复后再打包")
            print("  可设置环境变量 VCS_SKIP_TESTS=1 跳过测试")
            sys.exit(1)
    else:
        print("\n[1/3] 跳过测试套件（VCS_SKIP_TESTS=1）")

    # 5. 执行 PyInstaller 打包
    print("\n[2/3] 开始 PyInstaller 打包...")
    spec_file = project_root / "build.spec"
    if not spec_file.exists():
        print(f"✗ 打包配置文件不存在: {spec_file}")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--clean",
        "--noconfirm",
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
    ]
    print(f"执行: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd, cwd=str(project_root))
    except subprocess.CalledProcessError as e:
        print(f"✗ 打包失败: {e}")
        sys.exit(1)

    # 6. 验证产物
    print("\n[3/3] 验证打包产物...")
    exe_path = dist_dir / "医院虚拟会诊系统" / "医院虚拟会诊系统.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✓ 可执行文件已生成: {exe_path}")
        print(f"  文件大小: {size_mb:.1f} MB")
    else:
        print(f"✗ 未找到可执行文件: {exe_path}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ 打包完成")
    print("=" * 60)
    print(f"\n可执行程序路径：\n  {exe_path}")
    print(f"\n发布目录：\n  {dist_dir / '医院虚拟会诊系统'}")
    print("\n使用方法：双击 '医院虚拟会诊系统.exe' 启动桌面应用")


if __name__ == "__main__":
    main()
