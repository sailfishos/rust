# This spec is split into 2.

# There is some common header and then the real rust
# compiler/libraries are built in x86 root wrapped in an ifarch. The
# arm/aarch64 stubs are built at the end

# SFOS: If we're using the downloaded binaries then we don't define this
%define sfos 1
# if there is no rust available then define rust_use_bootstrap 1 in the prjconf
# For hacking purposes
%define rust_use_bootstrap 1
%define bootstrap_arches i486

%global bootstrap_rust 1.52.1
%global bootstrap_cargo 1.52.1

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html

%global rust_version 1.52.1

%ifarch %ix86
%define xbuildjobs %{nil}
%else
%ifarch %{arm}
%define xbuildjobs %{nil}
%else
%ifarch aarch64
# Limit build jobs in order to not exhaust memory on builds. JB#50504
%define xbuildjobs -j 4
%endif
%endif
%endif

%global rust_arm_triple armv7-unknown-linux-gnueabihf
%global rust_aarch64_triple aarch64-unknown-linux-gnu
%global rust_x86_triple i686-unknown-linux-gnu

%define build_armv7 0
%define build_aarch64 0

%global python python3

# LLDB isn't available everywhere...
%bcond_without lldb

Name:           rust
Version:        %{rust_version}+git1
Release:        1
Summary:        The Rust Programming Language
License:        (ASL 2.0 or MIT) and (BSD and MIT)
# ^ written as: (rust itself) and (bundled libraries)
URL:            https://www.rust-lang.org

%global rustc_package rustc-%{rust_version}-src
Source0:        rustc-%{rust_version}-src.tar.gz
Source100:      rust-%{rust_version}-i686-unknown-linux-gnu.tar.gz
Source200:      README.md

Patch2: 0002-Set-proper-llvm-targets.patch
Patch3: 0003-Disable-statx-for-all-builds.-JB-50106.patch
Patch4: 0004-Scratchbox2-needs-to-be-able-to-tell-rustc-the-defau.patch
Patch5: 0005-Cargo-Force-the-target-when-building-for-CompileKind-Host.patch
#Patch6: 0006-Provide-ENV-controls-to-bypass-some-sb2-calls-betwee.patch
# This is the real rustc spec - the stub one appears near the end.
%ifarch %ix86

#SFOS : our rust_use_bootstrap puts them into /usr
%if 0%{?rust_use_bootstrap}
%global bootstrap_root rust-%{rust_version}-%{rust_x86_triple}
%global local_rust_root %{_builddir}/%{bootstrap_root}/usr
%global bootstrap_source rust-%{rust_version}-%{rust_x86_triple}.tar.gz
%else
%global local_rust_root /usr
BuildRequires:  cargo >= %{bootstrap_cargo}
BuildRequires:  %{name} >= %{bootstrap_rust}
%endif

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

# Disable non-x86 build
ExcludeArch:    armv7hl
ExcludeArch:    aarch64

# Virtual provides for folks who attempt "dnf install rustc"
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

# Don't strip the rlibs as this fails for cross-built libraries
%define __strip /bin/true

%global rustflags -Clink-arg=-Wl,-z,relro,-z,now

%description
Rust is a systems programming language that runs blazingly fast, prevents
segfaults, and guarantees thread safety.

This package includes the Rust compiler and documentation generator.


%package std-static-%{rust_x86_triple}
# This package is built as an i486.rpm and provides the native libs
Provides: rust-std-static
Summary:        Standard library for Rust

%description std-static-%{rust_x86_triple}
This package includes the standard libraries for building
%{rust_x86_triple} applications written in Rust.

%if 0%{?build_armv7}
%package std-static-%{rust_arm_triple}
Summary:        Standard library for Rust

%description std-static-%{rust_arm_triple}
This package includes the standard libraries for building
%{rust_arm_triple} applications written in Rust.
%endif

%if 0%{?build_aarch64}
%package std-static-%{rust_aarch64_triple}
Summary:        Standard library for Rust

%description std-static-%{rust_aarch64_triple}
This package includes the standard libraries for building
%{rust_aarch64_triple} applications written in Rust.
%endif

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
#SFOS : our rust_use_bootstrap puts them into /usr
%if 0%{?rust_use_bootstrap}
%setup -q -n %{bootstrap_root} -T -b 100
./install.sh --components=cargo,rustc,rust-std-%{rust_x86_triple} \
  --prefix=%{local_rust_root} --disable-ldconfig
test -f '%{local_rust_root}/bin/cargo'
test -f '%{local_rust_root}/bin/rustc'
%endif

%setup -q -n %{rustc_package}

%patch2 -p1
%patch3 -p1
%patch4 -p1
%patch5 -p1
#%patch6 -p1

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

# FIXME: Do we still need this? -xfade
# Static linking to distro LLVM needs to add -lffi
# https://github.com/rust-lang/rust/issues/34486
#sed -i.ffi -e '$a #[link(name = "ffi")] extern {}' \
#  src/librustc_llvm/lib.rs

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
# We set these to be blank as rust will set appropriate values when
# invoking either the 'native' x86 or a suitable cross compiler.
# Leaving the x86 values causes problems when building the arm/aarch64 libs
CFLAGS=
CXXFLAGS=
FFLAGS=

# We're going to override --libdir when configuring to get rustlib into a
# common path, but we'll fix the shared libraries during install.
%global common_libdir %{_prefix}/lib
%global rustlibdir %{common_libdir}/rustlib

# full debuginfo is exhausting memory; just do libstd for now
# https://github.com/rust-lang/rust/issues/45854
# Limit memory usage for aarch64 build even more. JB#50504
%ifarch aarch64
%define enable_debuginfo --debuginfo-level=0 --debuginfo-level-rustc=0 --debuginfo-level-std=0 --debuginfo-level-tools=0 --debuginfo-level-tests=0
%else
%define enable_debuginfo --debuginfo-level=0 --debuginfo-level-std=2 --disable-debuginfo --disable-debuginfo-only-std --disable-debuginfo-tools --disable-debuginfo-lines
%endif


# arm cc needs to find ld so ensure PATH points to /opt/cross/bin too
PATH=/opt/cross/bin/:$PATH

###
# xfade spotted this snippet in suse rust.spec to validate the local rebuild
# Sometimes we may be rebuilding with the same compiler,
# setting local-rebuild will skip stage0 build, reducing build time
# if [ $(%{rust_root}/bin/rustc --version | sed -En 's/rustc ([0-9].[0-9][0-9].[0-9]).*/\1/p') = '%{version}' ]; then
# sed -i -e "s|#local-rebuild = false|local-rebuild = true|" config.toml;
# fi
###

# The configure macro sets CFLAGS to x86 which causes the ARM target to fail
# FIXME: disabled arm build for now. -xfade
./configure --prefix=/usr --exec-prefix=/usr --bindir=/usr/bin --sbindir=/usr/sbin --sysconfdir=/etc --datadir=/usr/share --includedir=/usr/include --libdir=/usr/lib --libexecdir=/usr/libexec --localstatedir=/var --sharedstatedir=/var/lib --mandir=/usr/share/man --infodir=/usr/share/info \
 --disable-option-checking \
  --libdir=%{common_libdir} \
  --build=%{rust_x86_triple} --host=%{rust_x86_triple}\
%if 0%{?build_aarch64}
  --target=%{rust_x86_triple},%{rust_arm_triple}\,%{rust_aarch64_triple}\
%else
  --target=%{rust_x86_triple}\
%endif
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
  --llvm-root=/usr/ \
  --enable-parallel-compiler \
  --set target.%{rust_x86_triple}.cc=/usr/bin/cc \
  --set target.%{rust_x86_triple}.ar=/usr/bin/ar \
%if 0%{?build_armv7}
  --set target.%{rust_arm_triple}.cc=/opt/cross/bin/armv7hl-meego-linux-gnueabi-cc \
  --set target.%{rust_arm_triple}.ar=/opt/cross/bin/armv7hl-meego-linux-gnueabi-ar \
%endif
%if 0%{?build_aarch64}
  --set target.%{rust_aarch64_triple}.cc=/opt/cross/bin/aarch64-meego-linux-gnu-cc \
  --set target.%{rust_aarch64_triple}.ar=/opt/cross/bin/aarch64-meego-linux-gnu-ar \
%endif
  --set build.verbose=2

%{python} ./x.py %{xbuildjobs} build


%install
export RUSTFLAGS="%{rustflags}"
CFLAGS=
CXXFLAGS=
FFLAGS=

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
(cd "%{buildroot}%{rustlibdir}/%{rust_x86_triple}/lib" &&
 find ../../../../%{_lib} -maxdepth 1 -name '*.so' |
 while read lib; do
   if [ -f "${lib##*/}" ]; then
     # make sure they're actually identical!
     cmp "$lib" "${lib##*/}"
     ln -v -f -s -t . "$lib"
   fi
 done)

# The non-x86 .so files would be used by rustc if it had been built
# for those targets
%if 0%{?build_armv7}
rm %{buildroot}%{rustlibdir}/%{rust_arm_triple}/lib/*.so
%endif
%if 0%{?build_aarch64}
rm %{buildroot}%{rustlibdir}/%{rust_aarch64_triple}/lib/*.so
%endif

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
# Disabled for efficient rebuilds until the hanging fix is completed
%if 0
%ifarch %ix86
%{?cmake_path:export PATH=%{cmake_path}:$PATH}
%{?rustflags:export RUSTFLAGS="%{rustflags}"}

# The results are not stable on koji, so mask errors and just log it.
%{python} ./x.py test --no-fail-fast || :
%{python} ./x.py test --no-fail-fast cargo || :
%endif
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
%dir %{rustlibdir}/%{rust_x86_triple}
%dir %{rustlibdir}/%{rust_x86_triple}/lib
%{rustlibdir}/%{rust_x86_triple}/lib/*.so
#%%exclude %%{_bindir}/*miri

%files std-static-%{rust_x86_triple}
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_x86_triple}
%dir %{rustlibdir}/%{rust_x86_triple}/lib
%{rustlibdir}/%{rust_x86_triple}/lib/*.rlib

%if 0%{?build_armv7}
%files std-static-%{rust_arm_triple}
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_arm_triple}
%dir %{rustlibdir}/%{rust_arm_triple}/lib
%{rustlibdir}/%{rust_arm_triple}/lib/*.rlib
%endif

%if 0%{?build_aarch64}
%files std-static-%{rust_aarch64_triple}
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_aarch64_triple}
%dir %{rustlibdir}/%{rust_aarch64_triple}/lib
%{rustlibdir}/%{rust_aarch64_triple}/lib/*.rlib
%endif

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

# This is the non x86 spec to produce dummy rust/cargo binaries
%else

# The rust package tags
# The requires should specify = %%{version}-%%{release} but they are repackaged from
# cross-rust and we can't specify the release in OBS
Requires:       %{name}-std-static = %{version}
# There should be an = %version dependency for external deployment but the cross-
# packaging doesn't work properly
Requires:       %{name}-std-static-%{rust_x86_triple}

%description
A stub of rust for use in scratchbox2

%package -n cargo
Summary:        Rust's package manager and build tool
Requires:       rust

%description -n cargo
A stub of cargo for use in scratchbox2

%prep
%build
%install
mkdir -p %{buildroot}%{_bindir}
cat <<'EOF' >%{buildroot}%{_bindir}/rustc
#!/bin/bash
echo "This is the stub rustc. If you see this, scratchbox2 is not working. Called as"
echo $0 "$@"
EOF
cat <<'EOF' >%{buildroot}%{_bindir}/cargo
#!/bin/bash
echo "This is the stub cargo. If you see this, scratchbox2 is not working. Called as"
echo $0 "$@"
EOF
mkdir %{buildroot}/.cargo
cat <<'EOF' > %{buildroot}/.cargo/config
[target.i686-unknown-linux-gnu]
linker = "i686-unknown-linux-gnu-gcc"
EOF
chmod 755 %{buildroot}%{_bindir}/*

%files
%defattr(-,root,root,0755)
%{_bindir}/rustc

%files -n cargo
%defattr(-,root,root,0755)
%{_bindir}/cargo
/.cargo
%endif
