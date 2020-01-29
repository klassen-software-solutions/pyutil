#!/usr/bin/env bash

# Run this when you wish to download the latest copy of the build system.

# Parse the command line options

set -e

_usage()
{
    echo "Usage: update-build-system.sh [--create] [--branch <branch>]"
    exit 255
}

forceCreate=0
branch="master"

while [ $# -gt 0 ]; do
    case "$1" in
        --create)
            forceCreate=1
            ;;
        --branch)
            if [ $# -lt 2 ]; then
                _usage
            fi
            branch="$2"
            shift
            ;;
        *)
            _usage
            ;;
    esac
    shift
done

# Determine that we are in the correct directory.

if [ ! -d "BuildSystem" ]; then
    if [ $forceCreate -eq 0 ]; then
        echo "You must run this from the project root directory. Or add the '--create' parameter"
        echo "if you wish to create the directory here."
        exit 255
    fi
fi

# Add some debugging output

url="https://github.com/klassen-software-solutions/BuildSystem/archive/$branch.zip"
echo "Downloading new BuildSystem..."
echo "   forceCreate=$forceCreate"
echo "   branch=$branch"
echo "   url=$url"

# Backup the existing directory.

if [ -d BuildSystem.bak ]; then
    rm -rf BuildSystem.bak
fi
if [ -d BuildSystem ]; then
    mv BuildSystem BuildSystem.bak
fi

# Download and extract the new version.

filename=$(basename $url)
curl -L $url > $filename
unzip $filename
directory="BuildSystem-${branch//\//-}"
if [ ! -d "$directory/BuildSystem" ]; then
    echo "Could not find BuildSystem within directory $directory"
    exit 255
fi
mv "$directory/BuildSystem" BuildSystem

# Cleanup

rm -rf "$directory"
rm -rf "$filename"
