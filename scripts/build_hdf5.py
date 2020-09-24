#!/usr/bin/env python3
"""
Compile HDF5 library

Be sure environment variables are set for your desired compiler.
Use the full compiler path if it's not getting the right compiler.

* FC: Fortran compiler name or path
* CC: C compiler name or path
"""
import typing as T
import sys
import os
import subprocess
import shutil
import argparse
import tempfile
from pathlib import Path

# ========= user parameters ======================
BUILDDIR = "build"
HDF5_TAG = "1.12/master"


# ========= end of user parameters ================

nice = ["nice"] if sys.platform == "linux" else []


def cli():
    p = argparse.ArgumentParser(description="Compile HDF5 library")
    p.add_argument(
        "compiler",
        help="compiler to build libraries for",
        choices=["gcc", "intel", "ibmxl"],
    )
    p.add_argument("-prefix", help="top-level directory to install libraries under")
    p.add_argument(
        "-workdir",
        help="top-level directory to build under (can be deleted when done)",
        default=tempfile.gettempdir(),
    )
    P = p.parse_args()

    compiler = P.compiler

    prefix = P.prefix if P.prefix else f"~/lib_{P.compiler}"

    if compiler == "gcc":
        env = gcc_compilers()
    elif compiler == "intel":
        env = intel_compilers()
    elif compiler == "ibmxl":
        env = ibmxl_compilers()
    else:
        raise ValueError(f"unknown compiler {compiler}")

    hdf5(
        {"prefix": Path(prefix).expanduser(), "workdir": Path(P.workdir).expanduser()},
        env=env,
    )


def hdf5(dirs: T.Dict[str, Path], env: T.Mapping[str, str]):
    """ build and install HDF5
    some systems have broken libz and so have trouble extracting tar.bz2 from Python.
    To avoid this, we git clone the release instead.
    """

    use_cmake = False
    name = "hdf5"
    install_dir = dirs["prefix"] / name
    source_dir = dirs["workdir"] / name
    build_dir = source_dir / BUILDDIR
    git_url = "https://bitbucket.hdfgroup.org/scm/hdffv/hdf5.git"

    git_download(source_dir, git_url, HDF5_TAG)

    if use_cmake or os.name == "nt":
        # this also works for Intel oneAPI with Ninja on Windows
        # NOTE: CMake Parallel builds fail for Make and Ninja
        # NOTE: Make and Ninja will both build repeatedly on each build command
        cmd0 = [
            "cmake",
            f"-S{source_dir}",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            "-DBUILD_SHARED_LIBS:BOOL=false",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DHDF5_BUILD_FORTRAN:BOOL=true",
            "-DHDF5_BUILD_CPP_LIB:BOOL=false",
            "-DHDF5_BUILD_TOOLS:BOOL=false",
            "-DBUILD_TESTING:BOOL=false",
            "-DHDF5_BUILD_EXAMPLES:BOOL=false",
        ]

        cmd1 = ["cmake", "--build", str(build_dir), "--", "-j1"]
        # disable parallel due to HDF5 CMakeLists bugs

        cmd2 = ["cmake", "--install", str(build_dir)]

        # this unusual configure command is necessary due to bugs with HDF5 CMakeLists.
        build_dir.mkdir(exist_ok=True)
        subprocess.check_call(nice + cmd0, cwd=build_dir, env=env)
    else:
        cmd0 = [
            "./configure",
            f"--prefix={install_dir}",
            "--enable-fortran",
            "--enable-build-mode=production",
        ]
        cmd1 = ["make", "-j"]
        cmd2 = ["make", "-j", "install"]
        subprocess.check_call(nice + cmd0, cwd=source_dir, env=env)

    subprocess.check_call(nice + cmd1, cwd=source_dir)
    subprocess.check_call(nice + cmd2, cwd=source_dir)


def git_download(path: Path, repo: str, tag: str):
    """
    Use Git to download code repo.
    """
    GITEXE = shutil.which("git")

    if not GITEXE:
        raise FileNotFoundError("Git not found.")

    git_version = (
        subprocess.check_output([GITEXE, "--version"], universal_newlines=True)
        .strip()
        .split()[-1]
    )
    print("Using Git", git_version)

    if path.is_dir():
        # don't use "git -C" for old HPC
        ret = subprocess.run([GITEXE, "checkout", tag], cwd=str(path))
        if ret.returncode != 0:
            ret = subprocess.run([GITEXE, "fetch"], cwd=str(path))
            if ret.returncode != 0:
                raise RuntimeError(
                    f"could not fetch {path}  Maybe try removing this directory."
                )
            subprocess.check_call([GITEXE, "checkout", tag], cwd=str(path))
    else:
        # shallow clone
        if tag:
            subprocess.check_call(
                [GITEXE, "clone", repo, "--branch", tag, "--single-branch", str(path)]
            )
        else:
            subprocess.check_call([GITEXE, "clone", repo, "--depth", "1", str(path)])


def get_compilers(compiler_name: str, **kwargs) -> T.Mapping[str, str]:
    """ get paths to compilers

    Parameters
    ----------

    compiler_name: str
        arbitrary string naming compiler--to give useful error message when compiler not found.
    """
    env = os.environ

    for k, v in kwargs.items():
        c = env.get(k, "")
        if v not in c:
            c = shutil.which(v)
        if not c:
            raise FileNotFoundError(
                f"Compiler {compiler_name} was not found: {k}."
                " Did you load the compiler shell environment first?"
            )
        env.update({k: c})

    return env


def gcc_compilers() -> T.Mapping[str, str]:
    return get_compilers("GNU", FC="gfortran", CC="gcc", CXX="g++")


def intel_compilers() -> T.Mapping[str, str]:
    return get_compilers(
        "Intel",
        FC="ifort",
        CC="icl" if os.name == "nt" else "icc",
        CXX="icl" if os.name == "nt" else "icpc",
    )


def ibmxl_compilers() -> T.Mapping[str, str]:
    return get_compilers("IBM XL", FC="xlf", CC="xlc", CXX="xlc++")


if __name__ == "__main__":
    cli()