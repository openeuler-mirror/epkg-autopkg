# autopkg project

One single repo for adding packages.

## cli interface

autopkg [--recursive] [--parse] [--build-feedback] [--build] UPSTREAM-NAME|DIR|URL --output YAML-DIR

## features

Support multiple build system/language registry
Create one parse-xxx.py file per category:
- c/c++ build systems (reuse autospec)
- python
- java
- javascript/typescript
- golang
- rust
- ruby
- perl
- haskell
- lua
- ...

## each parse-xxx.py
- input: name|dir
- output: package json (like final yaml, with more internal data)

## top level logic

    main
    cmdline parsing
    download url to local dir

    add_all_language
    add_one_language
    merge jsons, output package yaml/spec
    general build fail feedback

    call above for missing depends

## buildRequires type annotation

The internal buildRequires should have type annotation
- pkgconfig(xxx)
- python3dist(xxx)
- rubygem(xxx)
- cmake(xxx)
- mvn(xxx)
- golang(xxx)
- crate(xxx)
- perl(xxx)
- /bin/bash
- ...
- plain rpm package name

So that the common logic can resolve depends recursively.

## build systems in future yaml output

- buildSystem based
- auto buildSystem detection (together with programming language detection)

- minimal yaml (不用写%configure, %make, ...),
  with optional customizable phases/hooks (/c/os/NixOS/nixpkgs/pkgs/stdenv/generic/setup.sh)
- auto output files split (/c/os/NixOS/nixpkgs/pkgs/build-support/setup-hooks/multiple-outputs.sh)

e.g. /c/os/NixOS/nixpkgs/pkgs/applications/audio/flac/default.nix

```
{ lib, stdenv, fetchurl, fetchpatch, libogg }:

stdenv.mkDerivation rec {
  pname = "flac";
  version = "1.3.3";

  src = fetchurl {
    url = "http://downloads.xiph.org/releases/flac/${pname}-${version}.tar.xz";
    sha256 = "0j0p9sf56a2fm2hkjnf7x3py5ir49jyavg4q5zdyd7bcf6yq4gi1";
  };

  patches = [
    (fetchpatch {
      name = "CVE-2020-0499.patch";
      url = "https://github.com/xiph/flac/commit/2e7931c27eb15e387da440a37f12437e35b22dd4.patch";
      sha256 = "160qzq9ms5addz7sx06pnyjjkqrffr54r4wd8735vy4x008z71ah";
    })
  ];

  buildInputs = [ libogg ];

  #doCheck = true; # takes lots of time

  outputs = [ "bin" "dev" "out" "man" "doc" ];

  meta = with lib; {
    homepage = "https://xiph.org/flac/";
    description = "Library and tools for encoding and decoding the FLAC lossless audio file format";
    platforms = platforms.all;
    license = licenses.bsd3;
  };
}
```

## phases

    # config_fields.md
    unpack
        preUnpack
        postUnpack
    patch
        prePatch
        postPatch
    configure
        preConfigure
        postConfigure
    build
        preBuild
        postBuild
    check
        preCheck
        postCheck
    install
        preInstall
        postInstall
    fixup
        preFixup
        postFixup
    installCheck
        preInstallCheck
        postInstallCheck
    dist
        preDist
        postDist

## 映射 RPM spec 到 build systems and phases

1) 创建 buildSystem: rpmbuild
2) 映射 build phases

当buildSystem=rpmbuild时，有两种方案
1) 新增phase.prep，取代phase.unpack + phase.patch。
2) 自动识别%prep中的命令，把%setup放入phase.unpack，%patch放入phase.patch，其它语句酌情放入以上两个phase，或放入相应的pre/post phases。

如果自动化识别准确率高，优选方案(2)，为将来的分层定制预留空间。

    %prep       =>  (1) phase.prep or better (2) phase.unpack + phase.patch
    %conf       =>  phase.configure
    %build      =>  phase.build
    %install    =>  phase.install
    %check      =>  phase.check

## reference: spec convert tools

- https://gitee.com/openeuler/pkgporter
- https://gitee.com/openeuler/pyporter
- https://gitee.com/openeuler/perlporter
- https://gitee.com/openeuler/nodejsporter
- https://gitee.com/openeuler/rubyporter

- https://docs.fedoraproject.org/en-US/packaging-guidelines/Haskell/
- https://src.fedoraproject.org/rpms/cabal-rpm
- https://gitlab.com/fedora/sigs/go/go2rpm
- https://pagure.io/r2spec/
- /c/rpm-software-management/cargo2rpm
- /c/rpm-software-management/autospec
- /c/rpm-software-management/pyp2spec

## reference: type annotations in rpm repodata

```
# source packages
wfg@crystal ~/repodata% g -o 'rpm:entry name="[0-9_a-zA-Z-]+\(' de0f1bbbd530ff31c48e1403fde2db4d9eff25baa2c8498190f400f4c80f0cfa-primary.xml|sc
  47806 rpm:entry name="perl(
  11484 rpm:entry name="golang(
  10085 rpm:entry name="pkgconfig(
   9385 rpm:entry name="python3dist(
   3054 rpm:entry name="cmake(
   1923 rpm:entry name="mvn(
   1361 rpm:entry name="rubygem(
    943 rpm:entry name="tex(
    429 rpm:entry name="php(
    423 rpm:entry name="ruby(
    383 rpm:entry name="php-composer(
    125 rpm:entry name="crate(
     98 rpm:entry name="font(
     54 rpm:entry name="php-pear(
     20 rpm:entry name="php-channel(
     20 rpm:entry name="gawk(
     20 rpm:entry name="compiler(
      6 rpm:entry name="php-pecl(
      6 rpm:entry name="environment(
      4 rpm:entry name="llvm-devel(
      3 rpm:entry name="npm(
      3 rpm:entry name="mono(
      2 rpm:entry name="rhbuildsys(
      2 rpm:entry name="php-autoloader(
      2 rpm:entry name="nodejs(
      1 rpm:entry name="osgi(
      1 rpm:entry name="ocaml(
      1 rpm:entry name="kde4-macros(
      1 rpm:entry name="emacs(

# binary packages
wfg@crystal ~/repodata% g -o 'rpm:entry name="[0-9_a-zA-Z-]+\(' 45ae80d99816da5dfd71e925f5c92204420897b4b57d648a1ff8c6a9e85f0287-primary.xml|sc
   6789 rpm:entry name="tex(
   5526 rpm:entry name="font(
   3653 rpm:entry name="perl(
   1325 rpm:entry name="rtld(
    979 rpm:entry name="pkgconfig(
    780 rpm:entry name="gstreamer1(
    367 rpm:entry name="config(
    197 rpm:entry name="mimehandler(
    150 rpm:entry name="metainfo(
    142 rpm:entry name="application(
    134 rpm:entry name="python3dist(
    128 rpm:entry name="bundled(
    120 rpm:entry name="python(
     37 rpm:entry name="dnf-command(
     22 rpm:entry name="ruby(
     20 rpm:entry name="xserver-abi(
     16 rpm:entry name="rubygem(
     16 rpm:entry name="glib2(
      8 rpm:entry name="gtk3(
      8 rpm:entry name="cmake(
      7 rpm:entry name="libglusterfs0(
      6 rpm:entry name="nss(
      6 rpm:entry name="libglvnd(
      6 rpm:entry name="cmake-filesystem(
      6 rpm:entry name="boost-chrono(
      6 rpm:entry name="bind-libs(
      5 rpm:entry name="mariadb-server(
```

## reference: package manager stats

<https://libraries.io/>

Libraries.io monitors 9,578,063 open source
packages across 32 different package managers

Supported Package Managers

    npm             4.61M Packages
    Maven           614K Packages
    PyPI            539K Packages
    NuGet           499K Packages
    Go              463K Packages
    Packagist       419K Packages
    Rubygems        197K Packages
    Cargo           150K Packages
    CocoaPods       97.8K Packages
    Bower           69.1K Packages
    Pub             53.2K Packages
    CPAN            41K Packages
    CRAN            26.2K Packages
    Clojars         24.2K Packages
    conda           18.9K Packages
    Hackage         17.8K Packages
    Hex             16.2K Packages
    Meteor          13.3K Packages
    Homebrew        8.89K Packages
    Puppet          6.92K Packages
    Carthage        4.76K Packages
    SwiftPM         4.21K Packages
    Julia           3.04K Packages
    Elm             2.95K Packages
    Dub             2.76K Packages
    Racket          2.61K Packages
    Nimble          2.43K Packages
    Haxelib         1.7K Packages
    PureScript      770 Packages
    Alcatraz        462 Packages
    Inqlude         228 Packages
