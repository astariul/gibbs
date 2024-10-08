import setuptools


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

reqs = [
    "pyzmq>=22.3,<27.0",
    "msgpack~=1.0",
    "loguru~=0.6",
]

extras_require = {
    "test": ["pytest~=8.0", "pytest-asyncio~=0.18", "pytest-cov~=3.0", "coverage-badge~=1.0"],
    "hook": ["pre-commit~=4.0"],
    "lint": ["isort~=5.9", "black~=24.1", "flake518~=1.2", "darglint~=1.8"],
    "docs": ["mkdocs-material~=9.0", "mkdocstrings[python]~=0.18", "mike~=2.0"],
    "ex": ["fastapi~=0.75", "uvicorn~=0.17", "requests~=2.27", "transformers~=4.17"],
}
extras_require["all"] = sum(extras_require.values(), [])
extras_require["dev"] = (
    extras_require["test"] + extras_require["hook"] + extras_require["lint"] + extras_require["docs"]
)

setuptools.setup(
    name="gibbs",
    version="0.3.0.dev0",
    author="Nicolas REMOND",
    author_email="remondnicola@gmail.com",
    description="Scale your ML workers asynchronously across processes and machines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/astariul/gibbs",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=reqs,
    extras_require=extras_require,
)
