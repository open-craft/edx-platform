from setuptools import setup

setup(
    name="chem",
    version="0.1.1",
    packages=["chem"],
    install_requires=[
        "pyparsing==2.0.7",
        "numpy==1.6.2",
        "scipy==0.14.0",
        # Temporarily we comment this dependency, because it's not found in PyPi anymore, and we cannot
        # get it from an external repository.
        # nltk==2.0.6 is already required by requirements/edx/github.txt, that means that it will still
        # work as long as we run 'chem' after installing edx requirements.
        #"nltk==2.0.6",
    ],
)
