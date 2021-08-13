import os

from setuptools import find_packages, setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


__version__ = "0.0.1"

setup(
    name="gl_analytics",
    version=__version__,
    description="A tool to extract Kanban metrics from GitLab",
    entry_points={"console_scripts": ["gl-analytics=gl_analytics.__main__:main"]},
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://gitlab.com/gozynta/gl_analytics.git",
    author="Andrew Hamlin",
    author_email="andrew@gozynta.com",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "requests",
        "python-dotenv",
        "python-dateutil",
        "pandas",
        "matplotlib",
        "lockfile",
        "cachecontrol[filecache]",
    ],
)
