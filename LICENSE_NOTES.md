# Third-party redistribution

This source archive includes unmodified official scrcpy 5.0.1 win64 runtime files, including ADB and DLLs. Preserve tools/scrcpy/LICENSE.txt and the entire licenses directory. See THIRD_PARTY_NOTICES.md for component-specific terms, source references and source/build materials.

BridgeLab does not modify these upstream binaries, claim their authorship, or bundle a proprietary OPPO USB driver. The future PyInstaller output must also retain Python/Tcl/Tk/PyInstaller notices from its installed runtime; audit the generated bundle before public distribution.

v0.4 does not bundle a Python installer. The included PSF license remains a reference; use the actual frozen runtime notices for any future executable build.

v0.5 may download an official verified Python installer on first launch if needed and permitted by Windows policy; that installer is not included in this archive.
