#!/bin/bash

# To run:
# . ./setup-dev-linux.sh
# OR
# source ./setup-dev-linux.sh

check_python() {
    if ! command -v python &> /dev/null; then
        echo "python is not installed. Installing..."
        apt-get update
        apt-get -y install python3.10 
        alias python='/usr/bin/python3.10'
        echo "python installation complete."
    else
        local python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[0:2])))')
        major="${python_version%%.*}"
        minor="${python_version#*.}"

        if [ "$major" -lt 3 ] || [ "$minor" -lt 10 ]; then
            echo "python version is '$python_version'. Installing version 3.10..."
            apt-get update
            apt-get -y install python3.10 
            alias python='/usr/bin/python3.10'
            echo "python installation complete."
        fi
    fi
}

check_virtualenv() {
    if ! command -v virtualenv &> /dev/null; then
        echo "virtualenv is not installed. Installing..."
        python -m pip install --user virtualenv
        echo "virtualenv installation complete."
    fi
}

create_venv() {
    local env_name=${1:-".venv"}

    if [ -d "$env_name" ]; then
        echo "Virtual environment '$env_name' already exists. Aborting."
        return 1
    fi

    python -m venv "$env_name"
    source "./$env_name/bin/activate"
    pip install -U pip
}

activate_venv() {
    local env_name=${1:-".venv"}

    if [ ! -d "$env_name" ]; then
        echo "Virtual environment '$env_name' not found. Use '$0 create [env_name]' to create one."
        return 1
    fi

    source "./$env_name/bin/activate"
}

install_deps() {
    local env_name=${1:-".venv"}

    if [ ! -d "$env_name" ]; then
        echo "Virtual environment '$env_name' not found. Use '$0 create [env_name]' to create one."
        return 1
    fi

    source "./$env_name/bin/activate"

    if [ -f "src/requirements.txt" ]; then
        pip install -Ir src/requirements.txt
    fi

    if [ -f "requirements-dev.txt" ]; then
        pip install -Ir requirements-dev.txt
    fi
}

check_python
check_python
check_virtualenv
create_venv
activate_venv
install_deps