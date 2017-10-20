#!/bin/bash

cd ..
git checkout master
git pull
sphinx-apidoc --separate --force --no-toc -o doc/source bliss
cd doc
python setup.py build_sphinx
cd ..
git checkout gh-pages
\cp doc/build/html/*.html .
\cp doc/build/html/*.js .
\cp doc/build/html/*.inv .
\cp -r doc/build/html/_static .
git add *.html *.js _static *.inv

echo
echo "*** Documentation update complete ***"
echo
echo "Please review staged files, commit, and push"
echo "the changes (git push origin gh-pages)"
echo 
echo "When finished run 'git checkout master'"
