from setuptools import setup, find_packages, Extension

try:
    from Cython.Build import cythonize
    extensions = cythonize("hrm/hrmx.pyx", language_level=3)
except ImportError:
    extensions = [Extension("hrm.hrmx", ["hrm/hrmx.c"])]

setup(
    packages=find_packages(where="."),
    python_requires=">=3.9",
    package_data={"": ["*.json", "*.pyx"]},
    entry_points={"console_scripts": ["hrmi=hrm.__main__:main"]},
    ext_modules=extensions)
