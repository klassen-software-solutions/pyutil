#!/usr/bin/env bash

echo "#ifndef ${PREFIX}_all_h"
echo "#define ${PREFIX}_all_h"
echo
echo "/* This file is auto-generated and should not be edited. */"
echo
for fn in *.h*; do
	if echo "$fn" | grep -E '(^_.*|^all\.hp?p?$)' > /dev/null; then
		continue
	fi
    if echo "$fn" | grep -E '^.*\.hp?p?$' > /dev/null; then
        echo "#include \"$fn\""
    fi
done
echo
echo "#endif"
echo
