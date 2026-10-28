# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 医院虚拟会诊系统 (VCS)

打包命令（在项目根目录执行）：
    pyinstaller build.spec --clean --noconfirm

产物：
    dist/医院虚拟会诊系统/医院虚拟会诊系统.exe       （单机版可执行目录）
    dist/医院虚拟会诊系统/_internal/                （依赖与资源）

注意：
- 使用 onedir 模式而非 onefile，避免 jieba 词典缓存写入临时目录时的权限问题
- 数据文件（data/）通过 collect_data_files 收集
- 应用图标使用 application.icon（若不存在请提供或删除 icons 行）
"""
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集 jieba 词典数据
jieba_datas = collect_data_files('jieba')

# 收集 PyQt6 插件/翻译文件
pyqt_datas = collect_data_files('PyQt6')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # 数据目录（含示例患者、知识图谱、原始数据集等）
        ('data', 'data'),
        # 文档目录（可选，便于用户在程序内查阅）
        ('doc', 'doc'),
    ] + jieba_datas + pyqt_datas,
    hiddenimports=[
        # 显式声明动态导入的模块
        'src.adapters.his_adapter',
        'src.adapters.emr_adapter',
        'src.adapters.lis_adapter',
        'src.adapters.pacs_adapter',
        'src.adapters.base',
        'src.core.agent',
        'src.core.consultation',
        'src.core.evidence',
        'src.core.knowledge_graph',
        'src.core.medical_record',
        'src.core.moderator',
        'src.core.patient',
        'src.core.user',
        'src.core.session',
        'src.core.admin_config',
        'src.ui.consultation_view',
        'src.ui.knowledge_graph_dialog',
        'src.ui.main_window',
        'src.ui.patient_view',
        'src.ui.report_view',
        'src.ui.login_window',
        'src.ui.admin_view',
        'src.utils.data_loader',
    ] + collect_submodules('src'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除未使用的重型库以减小体积
        'matplotlib', 'tkinter', 'test', 'unittest',
        'pytest', 'IPython', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='医院虚拟会诊系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 关闭 UPX 压缩以避免 PyQt6 dll 被破坏
    console=False,  # 桌面 GUI 程序不弹控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='application.ico',  # 如有图标可启用
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='医院虚拟会诊系统',
)
