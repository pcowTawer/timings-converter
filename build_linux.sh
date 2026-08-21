#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACTS="$ROOT/_artifacts"
VENV_DIR="$ARTIFACTS/venv-linux"
WORK_DIR="$ARTIFACTS/work-linux"
SPEC_DIR="$ARTIFACTS/spec-linux"
DIST_DIR="$ARTIFACTS/dist-linux"
BUILDS_DIR="$ARTIFACTS/builds"
APP_NAME="Timings.Converter.Linux"
SCRIPT="$ROOT/timings_gui.py"

if [ ! -f "$SCRIPT" ]; then
    echo "Не найден файл $SCRIPT"
    echo "Если GUI-скрипт называется иначе, поправьте переменную SCRIPT в этом скрипте."
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating virtual environment in $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing/updating dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install --upgrade pyinstaller beautifulsoup4

echo "Building $APP_NAME ..."
"$VENV_DIR/bin/pyinstaller" --onefile --noconfirm \
    --name "$APP_NAME" \
    --workpath "$WORK_DIR" \
    --specpath "$SPEC_DIR" \
    --distpath "$DIST_DIR" \
    "$SCRIPT"

mkdir -p "$BUILDS_DIR"
cp "$DIST_DIR/$APP_NAME" "$BUILDS_DIR/$APP_NAME"
chmod +x "$BUILDS_DIR/$APP_NAME"

echo
echo "Готово: $BUILDS_DIR/$APP_NAME"
