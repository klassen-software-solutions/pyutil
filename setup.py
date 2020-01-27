import setuptools

with open("README.md", "r") as infile:
    long_description = infile.read()

setuptools.setup(
    name="pyutil-kss",
    version="0.0.1",
    author="Steven W. Klassen",
    author_email="klassens@acm.org",
    description="General Python utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/klassen-software-solutions/pyutil",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
