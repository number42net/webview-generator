#!/bin/bash
# WebView Generator - Docker Wrapper Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="webview-generator"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build Docker image if it doesn't exist or if --rebuild flag is passed
if [[ "$1" == "--rebuild" ]]; then
    echo "Rebuilding Docker image..."
    docker build --platform linux/amd64 -t "$IMAGE_NAME" -f "$SCRIPT_DIR/src/Dockerfile" "$SCRIPT_DIR"
    shift  # Remove --rebuild from arguments
elif ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Docker image not found. Building..."
    docker build --platform linux/amd64 -t "$IMAGE_NAME" -f "$SCRIPT_DIR/src/Dockerfile" "$SCRIPT_DIR"
fi

# Run the Python script inside Docker
# Extract install flag before passing to docker
INSTALL_FLAG=""
FILTERED_ARGS=()
APP_NAME=""
ICON_TMPFILE=""
NEXT_IS_ICON=false
for arg in "$@"; do
    if [[ "$arg" == "--install" ]]; then
        INSTALL_FLAG="true"
    elif [[ "$arg" == "--name" ]]; then
        NEXT_IS_NAME=true
        FILTERED_ARGS+=("$arg")
    elif [[ "$NEXT_IS_NAME" == "true" ]]; then
        APP_NAME="$arg"
        NEXT_IS_NAME=false
        FILTERED_ARGS+=("$arg")
    elif [[ "$arg" == "--icon" ]]; then
        NEXT_IS_ICON=true
        FILTERED_ARGS+=("$arg")
    elif [[ "$NEXT_IS_ICON" == "true" ]]; then
        NEXT_IS_ICON=false
        # Expand ~ and copy local icon files into the workspace so Docker can access them
        ICON_PATH="${arg/#\~/$HOME}"
        if [[ ! "$ICON_PATH" == http* ]] && [[ -f "$ICON_PATH" ]]; then
            ICON_EXT="${ICON_PATH##*.}"
            ICON_TMPFILE="$SCRIPT_DIR/.icon_tmp.$ICON_EXT"
            cp "$ICON_PATH" "$ICON_TMPFILE"
            FILTERED_ARGS+=("/workspace/.icon_tmp.$ICON_EXT")
        else
            FILTERED_ARGS+=("$arg")
        fi
    else
        FILTERED_ARGS+=("$arg")
    fi
done

# Add --build if --install is set
if [[ "$INSTALL_FLAG" == "true" ]]; then
    FILTERED_ARGS+=("--build")
fi

# Run Docker
docker run --rm \
    --platform linux/amd64 \
    -v "$SCRIPT_DIR:/workspace" \
    -w /workspace \
    -e GRADLE_USER_HOME=/workspace/.gradle_cache \
    -e IN_DOCKER=true \
    -e ANDROID_HOME=/opt/android-sdk \
    -e ANDROID_SDK_ROOT=/opt/android-sdk \
    "$IMAGE_NAME" \
    python3 -u src/generate_app.py "${FILTERED_ARGS[@]}"

# Clean up temporary icon file if one was created
if [[ -n "$ICON_TMPFILE" && -f "$ICON_TMPFILE" ]]; then
    rm -f "$ICON_TMPFILE"
fi

# If install flag was set, install on host after build
if [[ "$INSTALL_FLAG" == "true" && -n "$APP_NAME" ]]; then
    # Generate package name from app name (lowercase, replace spaces with nothing)
    PACKAGE_NAME="com.webview.$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]' | tr -d ' ')"
    APK_PATH="$SCRIPT_DIR/output/$APP_NAME/app/build/outputs/apk/debug/app-debug.apk"

    if [[ -f "$APK_PATH" ]]; then
        echo ""
        echo "============================================================"
        echo "Installing APK on device..."
        echo "============================================================"
        echo ""

        echo "Uninstalling existing app: $PACKAGE_NAME"
        adb uninstall "$PACKAGE_NAME" 2>/dev/null || true

        echo "Installing APK: $APK_PATH"
        if adb install "$APK_PATH"; then
            echo "Launching app: $PACKAGE_NAME"
            adb shell monkey -p "$PACKAGE_NAME" 1 >/dev/null 2>&1

            echo ""
            echo "============================================================"
            echo "✓ APK installed and launched successfully!"
            echo "============================================================"
            echo ""
        else
            echo ""
            echo "✗ Installation failed!"
            echo ""
        fi
    else
        echo "Error: APK not found at $APK_PATH"
    fi
fi
