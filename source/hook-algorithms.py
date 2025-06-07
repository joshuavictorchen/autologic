from PyInstaller.utils.hooks import collect_submodules

# tell PyInstaller to bundle every .py under the `algorithms` package
hiddenimports = collect_submodules("algorithms")
