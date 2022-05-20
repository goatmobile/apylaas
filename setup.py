#!/usr/bin/env python3

from pathlib import Path
from setuptools import setup

REPO_ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = REPO_ROOT / "apylaas"


templates = list(PACKAGE_DIR.glob("**/*.html"))
STATIC = PACKAGE_DIR / "static"
static_files = [
    STATIC / "favicon.ico",
    STATIC / "function.js",
    STATIC / "index.js",
    STATIC / "output.css",
]
web_files = static_files + templates
for file in web_files:
    if not file.exists():
        raise RuntimeError(
            f"File {file} does not exist (maybe the JS/CSS needs to be built?)"
        )
web_files = [str(x.relative_to(PACKAGE_DIR)) for x in web_files]

with open(REPO_ROOT / "README.md") as f:
    readme = f.read()

# https://setuptools.readthedocs.io/en/latest/setuptools.html
setup(
    name="apylaas",
    description="Any Python Library As A Service",
    long_description=readme,
    long_description_content_type="text/markdown",
    version="0.1.1",
    # author=about['__author__'],
    # author_email=about['__author_email__'],
    packages=["apylaas"],
    python_requires=">=3.7.*",
    install_requires=[],
    license="MIT",
    package_data={
        "": web_files,
    },
    entry_points={
        "console_scripts": ["apylaas = apylaas:main"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
    ],
)
