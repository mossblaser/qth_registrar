from setuptools import setup, find_packages

with open("qth_registrar/version.py", "r") as f:
    exec(f.read())

setup(
    name="qth_registrar",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/mossblaser/qth_registrar",
    author="Jonathan Heathcote",
    description="A registration server for Qth",
    license="GPLv2",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="mqtt asyncio home-automation messaging",

    # Requirements
    install_requires=["qth>=0.7.0"],
    
    # Scripts
    entry_points={
        "console_scripts": [
            "qth_registrar = qth_registrar.server:main",
        ],
    }
)
