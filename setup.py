from setuptools import setup, find_packages

NAME = "overgpu"
VERSION = 1.0

setup(
    name=NAME,
    version=VERSION,
    packages=find_packages(),
    zip_safe=True,
    python_requires=">=3.8",
    license="MIT",
    author="Nick Charron",
    scripts=[
        "scripts/overgpu.py",
    ],
)
