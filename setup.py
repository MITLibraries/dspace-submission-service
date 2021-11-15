from setuptools import find_packages, setup

setup(
    name="submitter",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Click",
        "boto3",
        "smart-open",
        (
            "dspace-python-client @ git+https://github.com/mitlibraries/"
            "dspace-python-client#egg=dspace-python-client"
        ),
    ],
    entry_points={"console_scripts": ["submitter=submitter.cli:main"]},
)
