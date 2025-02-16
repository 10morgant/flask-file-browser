#!/bin/bash

docker build -t files .

docker run --rm -p 5000:5000 -v ./test:/app/files -e ENABLE_UPLOAD=True -e ENABLE_NEW_FOLDER=True  files