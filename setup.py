from setuptools import setup, find_namespace_packages

setup(
    name="calibre_companion",
    version="0.1.0",
    packages=find_namespace_packages(include=['cli*', 'core*']),
    include_package_data=True,
    install_requires=[
        "Click",
        "SQLAlchemy",
        "beautifulsoup4",
        "requests",
        "Pillow",
        "psutil",
        "wmi; platform_system=='Windows'",  # Only install wmi on Windows
    ],
    entry_points={
        "console_scripts": [
            "calibre-companion=cli.main:main",
        ],
    },
) 