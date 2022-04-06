from setuptools import setup, find_packages
from pathlib import Path

import hrm

readme = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(name="hrm-interpreter",
      version=hrm.VERSION,
      description="Minimalist Human Resource Machine interpreter",
      long_description=readme.split("##")[0].strip(),
      long_description_content_type="text/markdown",
      licence="MIT",
      url="https://github.com/fpom/hrm",
      author="Franck Pommereau",
      author_email="franck.pommereau@univ-evry.fr",
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Developers",
                   "Topic :: Software Development :: Interpreters",
                   "License :: OSI Approved :: MIT License",
                   "Programming Language :: Python :: 3.8",
                   "Operating System :: OS Independent"],
      packages=find_packages(where="."),
      python_requires=">=3.8",
      install_requires=["colorama"],
      package_data={"" : ["*.json"]},
      entry_points={"console_scripts": ["hrmi=hrm.__main__:main"]})
