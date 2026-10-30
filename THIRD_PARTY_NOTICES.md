# Third-party notices for bundled Windows scrcpy 5.0.1

The portable package uses the unmodified official `scrcpy-win64-v5.0.1.zip` release from Genymobile (Windows x64). Keep upstream `LICENSE.txt` with the binaries. The original scrcpy source tag is available at <https://github.com/Genymobile/scrcpy/tree/v5.0.1>. This project does not modify the scrcpy payload.

## Components and licenses

| Component in upstream ZIP | Upstream version / origin | License and action |
|---|---|---|
| `scrcpy.exe`, `scrcpy-server`, helper scripts and artwork | scrcpy v5.0.1, Genymobile | Apache-2.0; see upstream `LICENSE.txt` and `licenses/Apache-2.0.txt`. |
| `SDL3.dll` | SDL 3.4.18 per the scrcpy v5.0.1 build script | zlib license; see `licenses/SDL-zlib-license.txt`. |
| `libusb-1.0.dll` | libusb 1.0.30 per build script | LGPL-2.1-or-later; see `licenses/LGPL-2.1.txt`. Distributed as a separate DLL. Corresponding source snapshot is included below. |
| `avutil-61.dll`, `avcodec-63.dll`, `avformat-63.dll`, `swresample-7.dll` | FFmpeg 9.0.2 per build script | LGPL-2.1-or-later for this configured build; see `licenses/LGPL-2.1.txt`. Build script disables GPL and nonfree components. Corresponding source snapshot is included below. |
| dav1d code linked into FFmpeg | dav1d 1.5.4 per build script; statically linked | BSD-2-Clause; see `licenses/BSD-2-Clause-dav1d.txt`. Corresponding source snapshot is included below. |
| zlib code linked into FFmpeg | FFmpeg configured with `--enable-zlib`; Windows build uses `-static` linker flags | zlib license; see `licenses/zlib-license.txt`. The FFmpeg recipe does not pin the zlib/toolchain version, so this build input is not reproducibly identified here. |
| `adb.exe`, `AdbWinApi.dll`, `AdbWinUsbApi.dll` | Android SDK Platform-Tools 37.0.1, fetched by official scrcpy build script | Retain the complete `licenses/platform-tools-NOTICE.txt` and `licenses/platform-tools-source.properties` extracted from the exact upstream Platform-Tools package. The NOTICE contains Apache-2.0 and third-party notices. |

## Source snapshots and build information

`licenses/sources/` contains git archive source snapshots for the LGPL and bundled dav1d components. They were created from upstream tags using `git archive`; hashes below are for these local archives, not the upstream release tarballs. Upstream scrcpy's exact build scripts used to build the Windows release are retained in `licenses/build-info/`.

| Source snapshot | Upstream tag / commit | SHA-256 of included archive |
|---|---|---|
| `sources/ffmpeg-n9.0.2-git-source.tar.gz` | `n9.0.2` / `946fcce07b6dcd0331c8cc609192aeff5e1924f8` | `3a3e4273b476f19fa0e5492fca3c3f0e23003a84b427dded829f54c43ad5216d` |
| `sources/libusb-v1.0.30-git-source.tar.gz` | `v1.0.30` / `87a55632db62c9bdc58cd31d3ccfa673f1bb017f` | `de84ba6807612f2bf421ab18ddb34000c9bfdd0f247bbdc2951779c442f6d58a` |
| `sources/dav1d-1.5.4-git-source.tar.gz` | `1.5.4` / `54706fc6bc0cdecab7e9593974a4039cc038fca7` | `dee4a6467777561acd1539dc8e814498ba94843fd46a0fae3be59836bfc7420e` |

Exact source URLs and upstream release archive SHA-256 values are recorded in the retained dependency scripts under `licenses/build-info/`. The local source snapshots are complete Git tree archives for those tags; they are not represented as byte-identical to the upstream tarball inputs. For FFmpeg and libusb, these source snapshots accompany separately distributed DLLs. The build configuration can be reconstructed from `build-info/ffmpeg.sh`, `libusb.sh`, `dav1d.sh`, `sdl.sh`, `adb_windows.sh`, and `build_windows.sh`.

## Reproducibility note

The FFmpeg build enables zlib and links statically; the exact MinGW zlib package version is not pinned by scrcpy's dependency scripts, so this dependency is not reproducibly identified here. Its zlib license is permissive and the license text is included. The original Android Platform-Tools package NOTICE and metadata are retained from the exact package. No OPPO or Google USB device driver is bundled; ADB user-space tools and Windows device drivers are separate.


## Python runtime

The v0.5 source ZIP contains no Python installer or frozen Python runtime. It uses the existing per-user runtime from an earlier BridgeLab setup, or a user-installed Python with Tcl/Tk. The included PSF license is a reference retained from earlier versions. The optional Windows executable builder must preserve notices for the actual Python/Tcl/Tk/PyInstaller runtime it freezes.

The v0.5 first-run helper may download the unmodified official CPython installer from python.org, require its PSF signature and pinned hash, and install a private runtime. The installer itself is not redistributed in this ZIP. See Python-3.12.10-LICENSE.txt for its license reference.
