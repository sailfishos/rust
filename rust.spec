# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html

%global rust_version 1.44.0

%ifarch %ix86
%global rust_triple i686-unknown-linux-gnu
%else
%ifarch %{arm}
%global rust_triple armv7-unknown-linux-gnueabihf
%else
%ifarch aarch64
%global rust_triple aarch64-unknown-linux-gnu
%endif
%endif
%endif

%global python python3

# LLDB isn't available everywhere...
%bcond_without lldb

Name:           rust
Version:        %{rust_version}+git4
Release:        1
Summary:        The Rust Programming Language
License:        (ASL 2.0 or MIT) and (BSD and MIT)
# ^ written as: (rust itself) and (bundled libraries)
URL:            https://www.rust-lang.org

%global rustc_package rustc-%{rust_version}-src
Source0:        rustc-%{rust_version}-src.tar.gz
Source100:      rust-%{rust_version}-i686-unknown-linux-gnu.tar.gz
Source101:      rust-%{rust_version}-armv7-unknown-linux-gnueabihf.tar.gz
Source102:      rust-%{rust_version}-aarch64-unknown-linux-gnu.tar.gz
Source200:      README.md

Patch1: 0001-Use-a-non-existent-test-path-instead-of-clobbering-d.patch
Patch2: 0002-Set-proper-llvm-targets.patch
Patch3: 0003-Disable-statx-for-all-builds.-JB-50106.patch

%global bootstrap_root rust-%{rust_version}-%{rust_triple}
%global local_rust_root %{_builddir}/%{bootstrap_root}/usr
%global bootstrap_source rust-%{rust_version}-%{rust_triple}.tar.gz

BuildRequires:  ccache
BuildRequires:  make
BuildRequires:  cmake
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  ncurses-devel
BuildRequires:  pkgconfig(libcurl)
# build.rs and boostrap/config.rs => cargo_native_static?
BuildRequires:  pkgconfig(liblzma)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(zlib)
BuildRequires:  python3-base
BuildRequires:  llvm-devel
BuildRequires:  libffi-devel

# make check needs "ps" for src/test/run-pass/wait-forked-but-failed-child.rs
BuildRequires:  procps

# debuginfo-gdb tests need gdb
BuildRequires:  gdb

# Virtual provides for folks who attempt "dnf install rustc"
Provides:       rustc = %{version}-%{release}
Provides:       rustc = %{version}-%{release}

# Always require our exact standard library
Requires:       %{name}-std-static = %{version}-%{release}

# The C compiler is needed at runtime just for linking.  Someday rustc might
# invoke the linker directly, and then we'll only need binutils.
# https://github.com/rust-lang/rust/issues/11937
Requires:       /usr/bin/cc

# ALL Rust libraries are private, because they don't keep an ABI.
%global _privatelibs lib(.*-[[:xdigit:]]{16}*|rustc.*)[.]so.*
%global __provides_exclude ^(%{_privatelibs})$
%global __requires_exclude ^(%{_privatelibs})$
%global __provides_exclude_from ^(%{_docdir}|%{rustlibdir}/src)/.*$
%global __requires_exclude_from ^(%{_docdir}|%{rustlibdir}/src)/.*$

# While we don't want to encourage dynamic linking to Rust shared libraries, as
# there's no stable ABI, we still need the unallocated metadata (.rustc) to
# support custom-derive plugins like #[proc_macro_derive(Foo)].  But eu-strip is
# very eager by default, so we have to limit it to -g, only debugging symbols.
%global _find_debuginfo_opts -g
%undefine _include_minidebuginfo

%global rustflags -Clink-arg=-Wl,-z,relro,-z,now

%description
Rust is a systems programming language that runs blazingly fast, prevents
segfaults, and guarantees thread safety.

This package includes the Rust compiler and documentation generator.


%package std-static
Summary:        Standard library for Rust

%description std-static
This package includes the standard libraries for building applications
written in Rust.


%package debugger-common
Summary:        Common debugger pretty printers for Rust
BuildArch:      noarch

%description debugger-common
This package includes the common functionality for %{name}-gdb and %{name}-lldb.


%package gdb
Summary:        GDB pretty printers for Rust
BuildArch:      noarch
Requires:       gdb
Requires:       %{name}-debugger-common = %{version}-%{release}

%description gdb
This package includes the rust-gdb script, which allows easier debugging of Rust
programs.


%if %with lldb

%package lldb
Summary:        LLDB pretty printers for Rust
BuildArch:      noarch
Requires:       lldb
Requires:       python3-lldb
Requires:       %{name}-debugger-common = %{version}-%{release}

%description lldb
This package includes the rust-lldb script, which allows easier debugging of Rust
programs.

%endif

%package -n cargo
Summary:        Rust's package manager and build tool
# Cargo is not much use without Rust
Requires:       rust

%description -n cargo
Cargo is a tool that allows Rust projects to declare their various dependencies
and ensure that you'll always get a repeatable build.


%prep
%ifarch %ix86
%setup -q -n %{bootstrap_root} -T -b 100
%else
%ifarch %{arm}
%setup -q -n %{bootstrap_root} -T -b 101
%else
%ifarch aarch64
%setup -q -n %{bootstrap_root} -T -b 102
%else
echo "No idea how to build for your arch..."
exit 1
%endif
%endif
%endif
./install.sh --components=cargo,rustc,rust-std-%{rust_triple} \
  --prefix=%{local_rust_root} --disable-ldconfig
test -f '%{local_rust_root}/bin/cargo'
test -f '%{local_rust_root}/bin/rustc'

%setup -q -n %{rustc_package}

%patch1 -p1
%patch2 -p1
%patch3 -p1

sed -i.try-py3 -e '/try python2.7/i try python3 "$@"' ./configure

rm -rf src/llvm-project/

# We never enable other LLVM tools.
rm -rf src/tools/clang
rm -rf src/tools/lld
rm -rf src/tools/lldb

# Remove other unused vendored libraries
# TODO: This is do be fixed still to have http2 enabled.
# rm -rf vendor/curl-sys/curl/
rm -rf vendor/jemalloc-sys/jemalloc/
rm -rf vendor/libz-sys/src/zlib/
rm -rf vendor/lzma-sys/xz-*/
rm -rf vendor/openssl-src/openssl/

# This only affects the transient rust-installer, but let it use our dynamic xz-libs
sed -i.lzma -e '/LZMA_API_STATIC/d' src/bootstrap/tool.rs

# rename bundled license for packaging
cp -a vendor/backtrace-sys/src/libbacktrace/LICENSE{,-libbacktrace}

# Static linking to distro LLVM needs to add -lffi
# https://github.com/rust-lang/rust/issues/34486
sed -i.ffi -e '$a #[link(name = "ffi")] extern {}' \
  src/librustc_llvm/lib.rs

# The configure macro will modify some autoconf-related files, which upsets
# cargo when it tries to verify checksums in those files.  If we just truncate
# that file list, cargo won't have anything to complain about.
find vendor -name .cargo-checksum.json \
  -exec sed -i.uncheck -e 's/"files":{[^}]*}/"files":{ }/' '{}' '+'

# Sometimes Rust sources start with #![...] attributes, and "smart" editors think
# it's a shebang and make them executable. Then brp-mangle-shebangs gets upset...
find -name '*.rs' -type f -perm /111 -exec chmod -v -x '{}' '+'


%build

export RUSTFLAGS="%{rustflags}"

# We're going to override --libdir when configuring to get rustlib into a
# common path, but we'll fix the shared libraries during install.
%global common_libdir %{_prefix}/lib
%global rustlibdir %{common_libdir}/rustlib

# full debuginfo is exhausting memory; just do libstd for now
# https://github.com/rust-lang/rust/issues/45854
%define enable_debuginfo --debuginfo-level=0 --debuginfo-level-rustc=0 --debuginfo-level-std=0 --debuginfo-level-tools=0 --debuginfo-level-tests=0

%configure --disable-option-checking \
  --libdir=%{common_libdir} \
  --build=%{rust_triple} --host=%{rust_triple} --target=%{rust_triple} \
  --python=%{python} \
  --local-rust-root=%{local_rust_root} \
  --enable-local-rebuild \
  --enable-llvm-link-shared \
  --enable-ccache \
  --enable-optimize \
  --disable-docs \
  --disable-compiler-docs \
  --disable-jemalloc \
  --disable-rpath \
  --disable-codegen-tests \
  --disable-verbose-tests \
  %{enable_debuginfo} \
  --enable-extended \
  --enable-vendor \
  --set rust.codegen-units-std=1 \
  --tools=cargo \
  --llvm-root=/usr/

%{python} ./x.py -j 4 build


%install
export RUSTFLAGS="%{rustflags}"

DESTDIR=%{buildroot} %{python} ./x.py install

# Make sure the shared libraries are in the proper libdir
%if "%{_libdir}" != "%{common_libdir}"
mkdir -p %{buildroot}%{_libdir}
find %{buildroot}%{common_libdir} -maxdepth 1 -type f -name '*.so' \
  -exec mv -v -t %{buildroot}%{_libdir} '{}' '+'
%endif

# The shared libraries should be executable for debuginfo extraction.
find %{buildroot}%{_libdir} -maxdepth 1 -type f -name '*.so' \
  -exec chmod -v +x '{}' '+'

# The libdir libraries are identical to those under rustlib/.  It's easier on
# library loading if we keep them in libdir, but we do need them in rustlib/
# to support dynamic linking for compiler plugins, so we'll symlink.
(cd "%{buildroot}%{rustlibdir}/%{rust_triple}/lib" &&
 find ../../../../%{_lib} -maxdepth 1 -name '*.so' |
 while read lib; do
   if [ -f "${lib##*/}" ]; then
     # make sure they're actually identical!
     cmp "$lib" "${lib##*/}"
     ln -v -f -s -t . "$lib"
   fi
 done)

# Remove installer artifacts (manifests, uninstall scripts, etc.)
find %{buildroot}%{rustlibdir} -maxdepth 1 -type f -exec rm -v '{}' '+'

# Remove backup files from %%configure munging
find %{buildroot}%{rustlibdir} -type f -name '*.orig' -exec rm -v '{}' '+'

# Remove unwanted documentation files (we already package them)
rm -f %{buildroot}%{_docdir}/%{name}/README.md
rm -f %{buildroot}%{_docdir}/%{name}/COPYRIGHT
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE-APACHE
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE-MIT
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE-THIRD-PARTY
rm -f %{buildroot}%{_docdir}/%{name}/*.old

# Create the path for crate-devel packages
mkdir -p %{buildroot}%{_datadir}/cargo/registry

%if %without lldb
rm -f %{buildroot}%{_bindir}/rust-lldb
rm -f %{buildroot}%{rustlibdir}/etc/lldb_*.py*
%endif

# Remove unwanted documentation files
rm -f %{buildroot}%{_bindir}/rustdoc
rm -fr %{buildroot}%{_mandir}/man1

%check
%ifarch %ix86
%{?cmake_path:export PATH=%{cmake_path}:$PATH}
%{?rustflags:export RUSTFLAGS="%{rustflags}"}

# The results are not stable on koji, so mask errors and just log it.
%{python} ./x.py test --no-fail-fast || :
%{python} ./x.py test --no-fail-fast cargo || :
%endif

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig


%files
%license COPYRIGHT LICENSE-APACHE LICENSE-MIT
%license vendor/backtrace-sys/src/libbacktrace/LICENSE-libbacktrace
%doc README.md
%{_bindir}/rustc
%{_libdir}/*.so
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_triple}
%dir %{rustlibdir}/%{rust_triple}/lib
%{rustlibdir}/%{rust_triple}/lib/*.so
%exclude %{_bindir}/*miri


%files std-static
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_triple}
%dir %{rustlibdir}/%{rust_triple}/lib
%{rustlibdir}/%{rust_triple}/lib/*.rlib

%files -n cargo
%license src/tools/cargo/LICENSE-APACHE src/tools/cargo/LICENSE-MIT src/tools/cargo/LICENSE-THIRD-PARTY
%doc src/tools/cargo/README.md
%{_bindir}/cargo
%{_sysconfdir}/bash_completion.d/cargo
%{_datadir}/zsh/site-functions/_cargo
%dir %{_datadir}/cargo
%dir %{_datadir}/cargo/registry


%files debugger-common
%dir %{rustlibdir}
%dir %{rustlibdir}/etc
%{rustlibdir}/etc/debugger_*.py*


%files gdb
%{_bindir}/rust-gdb
%{rustlibdir}/etc/gdb_*.py*
%exclude %{_bindir}/rust-gdbgui


%if %with lldb
%files lldb
%{_bindir}/rust-lldb
%{rustlibdir}/etc/lldb_*.py*
%endif
