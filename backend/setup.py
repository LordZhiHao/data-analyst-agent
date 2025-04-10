"""
Setup script for the Vanna SQL Agent package.
"""

from setuptools import setup, find_packages
import pathlib
import re

# Read version from app/__init__.py
init_path = pathlib.Path(__file__).parent / "app" / "__init__.py"
init_text = init_path.read_text()
version_regex = r"__version__ = ['\"]([^'\"]*)['\"]"
version = re.search(version_regex, init_text).group(1)

# Read requirements from requirements.txt
requirements_path = pathlib.Path(__file__).parent / "requirements.txt"
requirements = requirements_path.read_text().splitlines()
requirements = [r for r in requirements if not r.startswith("#") and r.strip()]

# Read long description from README.md
readme_path = pathlib.Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

setup(
    name="vanna-sql-agent",
    version=version,
    description="Natural language to SQL conversion with BigQuery execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/vanna-sql-agent",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "vanna-sql-agent=cli.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)