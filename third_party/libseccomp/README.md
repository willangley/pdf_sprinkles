# libseccomp

https://github.com/seccomp/libseccomp

This directory contains an unmodified libseccomp release tarball, and a Python
wheel built from it.

The libseccomp build doesn't make a wheel normally. To recreate it, you need to
add a few extra steps:

- Extract the release tarball
- Create a virtualenv, `$ python3 -m venv env`
- Invoke the virtualenv, `$ . env/bin/activate`
- Install dependencies,
    - `(env) $ pip install Cython`
    - `(env) $ pip install wheel`
- Configure, `(env) $ ./configure --enable-python`
- Make, `(env) $ make V=1`
- `(env) $ cd src/python`
- `(env) $ VERSION_RELEASE=2.5.2 pip wheel .`

## License

libseccomp is licensed under the GNU Lesser General Public License, v2.1. A copy
of the original license is included in this directory as LICENSE.
