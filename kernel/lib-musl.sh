# Funções comuns para compilar programas estáticos aarch64 com musl (initramfs de teste e
# reboot-recovery). Quem inclui define WORK, SYSROOT, DL, CROSS e JOBS.
# shellcheck shell=bash

MUSL_VERSION=1.2.5
MUSL_SHA256=a9a118bbe84d8764da0ea0d28b3ab3fae8477fc7e4085d90102b8596fc7c75e4

fetch() {
	local url="$1" sha="$2" file
	file="$DL/$(basename "$1")"
	mkdir -p "$DL"
	[[ -f "$file" ]] || curl -sSfL -o "$file.part" "$url"
	[[ -f "$file" ]] || mv "$file.part" "$file"
	echo "$sha  $file" | sha256sum -c --quiet -
}

extract() {
	local archive="$1" dest="$2"
	rm -rf "$dest"
	mkdir -p "$dest"
	tar -xf "$archive" -C "$dest" --strip-components=1
}

build_musl() {
	[[ -x "$SYSROOT/bin/musl-gcc" ]] && { provide_empty_libatomic; return; }
	fetch "https://musl.libc.org/releases/musl-$MUSL_VERSION.tar.gz" "$MUSL_SHA256"
	extract "$DL/musl-$MUSL_VERSION.tar.gz" "$WORK/musl"
	(cd "$WORK/musl" &&
		./configure --target=aarch64-linux-gnu --prefix="$SYSROOT" --disable-shared \
			--enable-wrapper=gcc CROSS_COMPILE="$CROSS" CC="${CROSS}gcc" >/dev/null &&
		make -s -j"$JOBS" && make -s install)
	provide_empty_libatomic
}

# O GCC 16 sempre linka -latomic_asneeded, e o cross do Fedora não traz a libatomic do
# alvo. Nada aqui usa a libatomic: um arquivo vazio basta.
provide_empty_libatomic() {
	[[ -f "$SYSROOT/lib/libatomic_asneeded.a" ]] || "${CROSS}ar" rc "$SYSROOT/lib/libatomic_asneeded.a"
}
