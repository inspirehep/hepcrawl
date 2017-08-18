#!/bin/bash -ei

# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

set -me

VENV_PATH=/hepcrawl_venv


restore_venv_tmp_code_rights() {
    if [[ "$BASE_USER_UID" != "" ]]; then
        BASE_USER_GID="${BASE_USER_GID:-$BASE_USER_UID}"
        echo "Restoring permissions of venv to $BASE_USER_UID:$BASE_USER_GID"
        /fix_rights --virtualenv "$BASE_USER_UID:$BASE_USER_GID"
        echo "Restoring permissions of codedir to $BASE_USER_UID:$BASE_USER_GID"
        /fix_rights --codedir "$BASE_USER_UID:$BASE_USER_GID"
        echo "Restoring permissions of tmpdir to $BASE_USER_UID:$BASE_USER_GID"
        /fix_rights --tmpdir "$BASE_USER_UID:$BASE_USER_GID"
        echo "Restoring permissions of vardir to $BASE_USER_UID:$BASE_USER_GID"
        /fix_rights --vardir "$BASE_USER_UID:$BASE_USER_GID"
    else
        echo "No BASE_USER_UID env var defined, skipping venv, codedir, tmpdir permission" \
            "restore."
    fi
}

forward_sigterm() {
    echo "Forwarding SIGTERM to $child"
    kill -SIGTERM "$child" &>/dev/null
    trap forward_sigterm SIGTERM
    wait "$child"
}


forward_sigint() {
    echo "Forwarding SIGINT to $child"
    kill -SIGINT "$child" &>/dev/null
    trap forward_sigint SIGINT
    wait "$child"
}


prepare_venv() {
    virtualenv "$VENV_PATH"
    source "$VENV_PATH"/bin/activate
    pip install --upgrade pip
    pip install --upgrade 'setuptools<36' wheel
}


main() {
    /fix_rights --virtualenv 'test:test'
    /fix_rights --codedir 'test:test'
    /fix_rights --tmpdir 'test:test'
    /fix_rights --vardir 'test:test'
    trap restore_venv_tmp_code_rights EXIT

    if ! [[ -f "$VENV_PATH/bin/activate" ]]; then
        prepare_venv
    else
        source "$VENV_PATH"/bin/activate
    fi

    find \( -name __pycache__ -o -name '*.pyc' \) -delete

    trap forward_sigterm SIGTERM
    trap forward_sigint SIGINT

    "$@" &
    child="$!"
    fg >/dev/null
}


main "$@"
