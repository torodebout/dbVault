from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="dbvault",
    version="1.0.0",
    author="Anas Douib",
    author_email="contact@adouib.ph",
    description="A command-line database backup utility",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/torodebout/dbvault",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dbvault=src.main:cli",
        ],
    },
)
