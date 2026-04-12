# WebView Generator

A Python tool to generate WebView-based Android apps from any URL. Perfect for quickly creating mobile apps from web applications.

## Features

- **Simple URL-to-APK**: Convert any website into an Android app
- **Play Store Icon Scraping**: Automatically fetch app icons from Google Play Store URLs
- **Full WebView Features**:
  - JavaScript enabled
  - File upload support
  - Pull-to-refresh
  - External link handling
  - Back button navigation
- **Gradle-based builds**: Standard Android build system
- **Dev-signed APKs**: Ready to install and test immediately

## Requirements

- Docker (that's it!)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd webview-generator
```

2. Install Docker:
   - macOS/Windows: [Docker Desktop](https://docs.docker.com/get-docker/)
   - Linux: [Docker Engine](https://docs.docker.com/engine/install/)

The Docker image will be built automatically on first use and contains everything needed (Python, Java 17, Android SDK, Gradle).

## Usage

### Basic Usage

Generate a project without building:
```bash
./build.sh --url https://example.com --name "My App"
```

### With Icon from File

```bash
./build.sh --url https://example.com --name "My App" --icon /path/to/icon.png
```

### With Icon from Play Store

The script can automatically fetch app icons from Google Play Store URLs:
```bash
./build.sh \
  --url https://example.com \
  --name "My App" \
  --icon "https://play.google.com/store/apps/details?id=com.example.app"
```

### Generate and Build APK

Add the `--build` flag to automatically build the APK after project generation:
```bash
./build.sh \
  --url https://example.com \
  --name "My App" \
  --icon icon.png \
  --build
```

### Build and Install via ADB

Add the `--install` flag to build the APK and immediately install it on a connected Android device via ADB. This implicitly enables `--build`, uninstalls any existing version of the app, installs the new APK, and launches it automatically:
```bash
./build.sh \
  --url https://example.com \
  --name "My App" \
  --icon icon.png \
  --install
```

### Custom Package Name

By default, package names are auto-generated from the app name. You can specify a custom package:
```bash
./build.sh \
  --url https://example.com \
  --name "My App" \
  --package com.mycompany.myapp
```

### Custom Output Directory

```bash
./build.sh \
  --url https://example.com \
  --name "My App" \
  --output /path/to/output
```

### Rebuild Docker Image

If you update the Dockerfile or want to rebuild the image:
```bash
./build.sh --rebuild
```

## Command-Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--url` | Yes | URL to load in the WebView |
| `--name` | Yes | App name (displayed to users) |
| `--icon` | No | Path to icon file or Play Store URL |
| `--output` | No | Output directory (default: `output`) |
| `--build` | No | Build APK after generation |
| `--install` | No | Build APK, install via ADB, and launch on connected device (implies `--build`) |
| `--package` | No | Custom package name (default: auto-generated) |

## Manual Build

If you didn't use the `--build` flag, you can manually build the APK using Docker:

```bash
docker run --rm \
  -v "$(pwd)/output/Your_App_Name:/project" \
  -v "$(pwd)/.gradle_cache:/root/.gradle" \
  -w /project \
  webview-generator-builder \
  ./gradlew assembleDebug
```

The APK will be located at:
```
output/Your_App_Name/app/build/outputs/apk/debug/app-debug.apk
```

### Rebuilding Docker Image

If you need to rebuild the Docker image (e.g., to update dependencies):

```bash
docker build -t webview-generator-builder -f src/Dockerfile .
```

## Installing the APK

### On Device

1. Transfer the APK to your Android device
2. Enable "Install from Unknown Sources" in Settings
3. Tap the APK to install

### Using ADB

```bash
adb install path/to/app-debug.apk
```

## Generated App Features

The generated WebView apps include:

- **JavaScript Support**: Full JavaScript execution
- **File Uploads**: Camera and file picker integration
- **Pull to Refresh**: Swipe down to reload
- **External Links**: Proper handling of `tel:`, `mailto:`, etc.
- **Back Navigation**: Back button goes to previous page in WebView
- **Network State**: Proper internet permission handling
- **Mixed Content**: Support for HTTP/HTTPS mixed content
- **Responsive**: Adapts to device orientation and screen size
- **Persistent Storage**: Cookies, localStorage, sessionStorage, and IndexedDB all persist
- Each WebView app has completely isolated storage from the system browser and other apps

## Customization

After generation, you can customize the app by editing:

- **MainActivity.kt**: Add custom WebView behavior, inject JavaScript, etc.
- **AndroidManifest.xml**: Add permissions, configure app properties
- **build.gradle**: Change SDK versions, add dependencies
- **res/**: Modify app icons, add strings, themes

## Troubleshooting

### Docker Not Found

1. Ensure Docker is installed and running
2. Test with: `docker --version`
3. Start Docker Desktop if on macOS/Windows

### Build Fails

1. Check Docker logs for errors
2. Try rebuilding the Docker image: `docker build -t webview-generator-builder -f src/Dockerfile .`
3. Check internet connection (Gradle downloads dependencies)
4. Clear Gradle cache: `rm -rf .gradle_cache`

### Icon Not Found

- Verify the Play Store URL is correct
- Try using a direct image file instead
- Check internet connection

### APK Won't Install

- Enable "Install from Unknown Sources"
- Uninstall previous version if exists
- Check device storage space

## Security Note

The generated apps use WebView with JavaScript enabled and accept all SSL certificates in mixed content mode. This is suitable for trusted URLs and development purposes. For production apps with sensitive data, consider:

- Implementing SSL pinning
- Restricting JavaScript execution
- Adding proper input validation
- Implementing security headers

## Examples

### Example 1: Simple Web App
```bash
./build.sh \
  --url https://mobile.twitter.com \
  --name "Twitter" \
  --icon "https://play.google.com/store/apps/details?id=com.twitter.android" \
  --build
```

### Example 2: Internal Tool
```bash
./build.sh \
  --url https://intranet.company.com/dashboard \
  --name "Company Dashboard" \
  --icon company_logo.png \
  --package com.company.dashboard \
  --build
```

### Example 3: Quick Prototype
```bash
./build.sh \
  --url http://localhost:3000 \
  --name "Dev App" \
  --build
```
