init:
	pip install -r requirements.txt

test:
	nosetests --with-coverage tests
