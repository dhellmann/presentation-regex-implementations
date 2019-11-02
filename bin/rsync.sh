#!/bin/bash

set -x

FILES="*.html css js lib plugin graphs/*.svg img fonts"

ssh doughellmann.com 'mkdir -p ~/doughellmann.com/presentations/regex-implementations'

rsync -av --progress $FILES doughellmann.com:~/doughellmann.com/presentations/regex-implementations/
