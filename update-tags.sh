#!/bin/sh

set -e

git fetch --tags upstream
git push --tags
