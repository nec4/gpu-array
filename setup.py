from setuptools import setup, find_packages
from setuptools.command.install import install
import os

NAME = "gpu_array"
VERSION = "0.0"


class InstallScript(install):
    def run(self):
        install.run(self)


with open("requirements.txt", "r") as f:
    install_requires = list(
        filter(lambda x: "#" not in x, (line.strip() for line in f))
    )

setup(
    name=NAME,
    version=VERSION,
    author="Nick Charron",
    author_email="charron.nicholas.e@gmail.com",
    url="https://github.com/nec4/overgpu",
    license="MIT",
    packages=find_packages(),
    install_requires=install_requires,
    zip_safe=True,
    cmdclass={"install": InstallScript},
    entry_points={
        "console_scripts": ["gpu-array = gpu_array.scripts.__main__:main"],
    },
)
