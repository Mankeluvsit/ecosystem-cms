#!/bin/sh
set -eu
chown -R cms:cms /data
exec runuser -u cms -- "$@"
