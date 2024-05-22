:: To run 
:: 
:: NB: If your python alias is 'py' instead of 'python', then run "DOSKEY python=py $1" before running the script
@echo off

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed.
    goto :eof
)

python -c "import sys; exit(1) if sys.version_info < (3, 10) else exit(0)"
if %errorlevel% equ 0 (
    goto :check_virtualenv
) else (
    echo Python %PYTHON_VERSION% is installed, but version 3.10 or higher is required.
    goto :eof
)

:check_virtualenv
    python -c "import venv" 2>nul
    if errorlevel 1 (
        echo. venv is not installed. Installing...
        python -m pip install --user venv
        echo. venv installation complete.
    )

:create_venv
    if exist ".venv" (
        goto :activate_venv
    )

    python -m venv ".venv"

:activate_venv
    call ".venv\Scripts\activate"

:install_deps
    python -m pip install -U pip
    
    if exist "src\requirements.txt" (
        python -m pip install -Ir src/requirements.txt
    )

    if exist "requirements-dev.txt" (
        python -m pip install -Ir requirements-dev.txt
    )

:end