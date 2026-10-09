# Firefox QD

Firefox main with a private Harmony FreeType build and triangular RGB text
sampling. No custom FreeType rasterizer or API changes are required. The panel
geometry is estimated, not measured.

The source checkout is `firefox-157.0.1/`, branch `freetype-lcd-geometry`, based on
`main`. `source.json` pins the official upstream repository and base commit.
`patches/firefox-harmony.patch` applies to that upstream commit; regenerate
it from committed source with `scripts/export-patch.py`.

Build with `MOZCONFIG=/home/rob/firefox/mozconfig ./mach build` from the source
checkout. `firefox-qd --qd-build` runs the result with a separate test profile;
add `--qd-mode gray` for ordinary grayscale. The normal launcher uses the
installed build at `~/.local/opt/firefox-qd`. To replace it, run `./mach package`
then `scripts/install.py --keep-previous` from this directory.

`scripts/check-browser.py --gpu` captures actual NVIDIA Wayland compositor
output at 150% scaling. Add `--advanced` for variable-font, canvas and scroll
checks. `scripts/build-freetype-probe.py` and `scripts/check-coverage.c` compare
LCD coverage with independently translated grayscale rasters. Test output
belongs in ignored `artifacts/` and `logs/` directories.

This is a local integration patch, not an upstream submission. The rebased
160.0a1 source has not been built or runtime-tested; the installed browser and
existing test binary remain the validated 157.0.1 build. Skia bounds now expand on both axes in the QD mode; direct FreeType probes
validate containment, but the updated browser paths still need runtime testing.
Upstream submission still requires general
geometry configuration, an optional bundled-library build, regression tests,
and validation of the supported platform configurations. The grayscale
experiment is preserved by `grayscale-experiment-2026-10-09` in this repository,
the source repository, and `/home/rob/freetype-geometry`.
