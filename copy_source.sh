#!/bin/bash

src="$1"
dst="$2/$(basename $1)"

sed $'/## @hidden/,$d' $src | grep -Pv '^\s*(?:#|(?:print|self\.info)(?=[^_\w])|$)' >$dst