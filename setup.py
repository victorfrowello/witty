from setuptools import setup, find_packages

setup(
    name="witty",
    version="1.0.0",
    description="Witty - Epistemic Formalization Engine: Convert natural language to formal logic",
    author="Victor Rowello",
    author_email="victor@rowello.com",
    url="https://github.com/victorfrowello/witty",
    license="GPL-3.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
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
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ]
)