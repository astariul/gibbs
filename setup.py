import setuptools


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

reqs = [
    "pyzmq~=22.3",
    "msgpack~=1.0",
    "loguru~=0.6",
]

extras_require = {
    "test": ["pytest~=7.0", "pytest-asyncio~=0.18", "pytest-cov~=3.0", "coverage-badge~=1.0"],
    "hook": ["pre-commit~=2.15"],
    "lint": ["isort~=5.9", "black~=22.1", "flake518~=1.2", "darglint~=1.8"],
    "docs": ["mkdocs-material~=8.1", "mkdocstrings~=0.16", "mike~=1.1"],
    "ex": ["fastapi~=0.75", "uvicorn~=0.17", "requests~=2.27", "transformers~=4.17"],
}
extras_require["all"] = sum(extras_require.values(), [])
extras_require["dev"] = (
    extras_require["test"] + extras_require["hook"] + extras_require["lint"] + extras_require["docs"]
)

setuptools.setup(
    name="gibbs",
    version="0.1.0",
    author="Nicolas REMOND",
    author_email="remondnicola@gmail.com",
    description="Easily scale your ML models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/astariul/gibbs",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=reqs,
    extras_require=extras_require,
)
