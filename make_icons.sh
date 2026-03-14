#!/bin/bash

inkscape icon-src/kaprao-favicon.svg --export-filename=extension/img/icon-16.png   -w 16  -h 16
inkscape icon-src/kaprao-favicon.svg --export-filename=extension/img/icon-32.png   -w 32  -h 32
inkscape icon-src/kaprao-favicon.svg --export-filename=extension/img/icon-48.png   -w 48  -h 48
inkscape icon-src/kaprao-favicon.svg --export-filename=extension/img/icon-128.png  -w 128 -h 128

inkscape icon-src/kaprao-off.svg --export-filename=extension/img/icon-16-off.png   -w 16  -h 16
inkscape icon-src/kaprao-off.svg --export-filename=extension/img/icon-32-off.png   -w 32  -h 32
inkscape icon-src/kaprao-off.svg --export-filename=extension/img/icon-48-off.png   -w 48  -h 48
inkscape icon-src/kaprao-off.svg --export-filename=extension/img/icon-128-off.png  -w 128 -h 128

inkscape icon-src/kaprao-favicon.svg --export-filename=icon-src/favicon-16.png  -w 16  -h 16
inkscape icon-src/kaprao-favicon.svg --export-filename=icon-src/favicon-32.png  -w 32  -h 32
inkscape icon-src/kaprao-favicon.svg --export-filename=icon-src/favicon-48.png  -w 48  -h 48

# inkscape icon-src/kaprao-safe-area.svg --export-filename=web/public/apple-touch-icon.png        -w 180 -h 180
# inkscape icon-src/kaprao-safe-area.svg --export-filename=web/public/apple-touch-icon-152.png    -w 152 -h 152
# inkscape icon-src/kaprao-safe-area.svg --export-filename=web/public/apple-touch-icon-167.png    -w 167 -h 167