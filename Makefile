default: build

build:
	python setup.py sdist bdist_wheel

version:
	@# prints version number
	@(python -c 'import pafy; print(pafy.__version__)')

upload:
	@# requires pypi auth
	python setup.py sdist bdist_wheel upload

register:
	@# requires pypi auth
	python setup.py register

install:
	@# system wide install
	sudo python setup.py install --record pafy_installed_filelist

vinstall:
	@# install from within virtualenv (no sudo)
	python setup.py install --record pafy_installed_filelist

uninstall:
	cat pafy_installed_filelist | xargs sudo rm -f
	sudo rm -f pafy_installed_filelist

clean:
	sudo rm -rf build/ dist/ *egg-info/ *.pyc __pycache__
	rm -f WASTE*.ogg WASTE*.temp
	rm -rf htmlcov
	find ./.tox | grep \\.pyc | xargs sudo rm -f
	find . | grep \\.pyc | xargs sudo rm -f
	find . | grep __pycache__ | xargs sudo rm -rf
