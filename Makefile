init:
	pip install -r requirements.txt
test:
	nosetests tests -v --with-coverage --cover-package=academictorrents

