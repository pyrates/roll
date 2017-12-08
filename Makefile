init:
	git submodule update --init

compile:
	cython -3 roll/core.pyx
	python setup.py build_ext --inplace

test:
	py.test -v
