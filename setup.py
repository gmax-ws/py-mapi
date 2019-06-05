import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='mapi',
    version='0.1',
    author="Marius Gligor",
    author_email="marius.gligor@gmail.com",
    description="Mail API utility package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gmax.go.ro",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
