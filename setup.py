from setuptools import setup, find_packages

setup(
    name='submitter',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points={
        'console_scripts': [
            'submitter=submitter.cli:hello'
        ]
    },
)
