#!/bin/sh

set -ex

n="$CPU_COUNT"

# -march=x86_64 and MPN_PATH are set enable a build product that is
# -portable across our CPUs
./configure --prefix="$PREFIX" \
            CFLAGS="-O2 -pedantic -fomit-frame-pointer -m64 -march=x86-64" \
            MPN_PATH="x86_64 generic"
make -j $n LDFLAGS="-Wl,-rpath-link,$PREFIX/lib"
make check
make install prefix="$PREFIX"
