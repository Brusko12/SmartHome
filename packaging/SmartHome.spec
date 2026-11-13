# Build on the target OS. PyInstaller does not cross-compile Windows executables.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root=Path(SPECPATH).parent
datas=[(str(root/'frontend'/'dist'),'frontend/dist'),
       (str(root/'backend'/'alembic'/'env.py'),'backend/alembic'),
       (str(root/'backend'/'alembic'/'script.py.mako'),'backend/alembic'),
       (str(root/'backend'/'alembic.ini'),'backend')]+[(str(p),'backend/alembic/versions') for p in (root/'backend'/'alembic'/'versions').glob('*.py')]+collect_data_files('tzdata')
a=Analysis([str(root/'launcher'/'main.py')],pathex=[str(root/'backend'),str(root)],
           binaries=[],datas=datas,hiddenimports=collect_submodules('app')+collect_submodules('uvicorn')+collect_submodules('tzdata')+['anyio._backends._asyncio'],
           hookspath=[],hooksconfig={},runtime_hooks=[],excludes=['tkinter','pytest','IPython','PySide6','PyQt5','pip'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='SmartHome',debug=False,bootloader_ignore_signals=False,
        strip=False,upx=False,console=False,disable_windowed_traceback=True,contents_directory='resources')
collect=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SmartHome-Release')
