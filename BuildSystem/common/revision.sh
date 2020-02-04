#!/usr/bin/env bash

_format_for_python()
{
    # shellcheck disable=SC2001
    #   Justification: Parameter expansion cannot handle the search and replace we require.
    echo "$1" | sed 's/M$/.dev/' | sed 's/-\([0-9]*\)-.*/.dev\1/'
}

# Determine the version format
if [ $# -gt 1 ]; then
    echo "usage: revision.sh [--format=python]"
    exit 255
fi

format="semantic"
if [ "$1" == "--format=python" ]; then
    format="python"
fi

# Obtain the version from the git tags

if git describe --tags --dirty=M >/dev/null 2>/dev/null; then
    newver=$(git describe --tags --dirty=M 2>/dev/null)
    if [ "$format" == "python" ]; then
        newver=$(_format_for_python "$newver")
    fi
else
    newver="0.0.0"
fi

# Allow override by environment variable
if [ x"$REVISION" != "x" ]; then
	newver=$REVISION
fi

# Update the REVISION file

if [ -f REVISION ]; then
    oldver=$(cat REVISION)
    if [ "$oldver" != "$newver" ]; then
        echo "$newver" > REVISION
    fi
else
    echo "$newver" > REVISION
fi

echo "$newver"
