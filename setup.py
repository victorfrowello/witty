from setuptools import setup, find_packages

setup(
    name="witty",
    version="0.1.0",
    description="Witty natural language formalization pipeline",
    author="Victor",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "python-dotenv",
        "pyyaml",
        "typing-extensions",
        "pydantic>=2.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0"
        ]
    }
)