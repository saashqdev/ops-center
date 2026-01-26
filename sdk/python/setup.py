"""
Ops-Center Plugin SDK for Python

Build powerful backend plugins for Ops-Center with ease.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

setup(
    name="ops-center-plugin-sdk",
    version="0.1.0",
    description="Official Python SDK for building Ops-Center plugins",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ops-Center Team",
    author_email="dev@ops-center.com",
    url="https://github.com/your-org/ops-center-oss",
    license="MIT",
    
    packages=find_packages(exclude=["tests", "examples"]),
    
    python_requires=">=3.9",
    
    install_requires=[
        "fastapi>=0.104.0",
        "pydantic>=2.0.0",
        "httpx>=0.25.0",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "jinja2>=3.1.0",
    ],
    
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
            "ruff>=0.1.0",
        ],
        "all": [
            "sqlalchemy>=2.0.0",
            "redis>=5.0.0",
            "celery>=5.3.0",
        ],
    },
    
    entry_points={
        "console_scripts": [
            "ops-center-plugin=ops_center_sdk.cli:main",
        ],
    },
    
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    
    keywords="ops-center plugin sdk backend api fastapi",
    
    project_urls={
        "Documentation": "https://docs.ops-center.com/plugins",
        "Source": "https://github.com/your-org/ops-center-oss",
        "Tracker": "https://github.com/your-org/ops-center-oss/issues",
    },
)
