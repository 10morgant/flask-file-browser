#!/bin/bash

docker build -t software .

docker run --rm -p 5000:5000 -v /home/tim/Github/personal/file_browser/test:/app/files -e ENABLE_UPLOAD=True -e ENABLE_NEW_FOLDER=True software