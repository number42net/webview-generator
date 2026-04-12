#!/usr/bin/env python3
"""
WebView Android App Generator
Generates a webview-based Android app from a URL
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from PIL import Image


class WebViewAppGenerator:
    def __init__(
        self,
        url: str,
        app_name: str,
        icon_source: str | None,
        output_dir: str = "output",
    ) -> None:
        self.url = url
        self.app_name = app_name
        self.package_name = self._generate_package_name(app_name)
        self.icon_source = icon_source
        self.output_dir = Path(output_dir)
        self.project_dir = self.output_dir / self._sanitize_filename(app_name)

    def _sanitize_filename(self, name: str) -> str:
        """Convert app name to a valid directory name"""
        return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")

    def _generate_package_name(self, app_name: str) -> str:
        """Generate package name from app name"""
        # Convert to lowercase, remove special chars, replace spaces with dots
        clean_name = re.sub(r"[^\w\s]", "", app_name.lower())
        clean_name = re.sub(r"\s+", ".", clean_name.strip())
        return f"com.webview.{clean_name}"

    def _download_playstore_icon(self, playstore_url: str) -> Path | None:
        """Download app icon from Play Store URL"""
        # Clean up URL - remove any shell escape characters
        playstore_url = playstore_url.replace("\\", "")

        print(f"Fetching icon from Play Store: {playstore_url}")

        try:
            # Fetch the Play Store page
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(playstore_url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML to find icon
            soup = BeautifulSoup(response.text, "lxml")

            # Try multiple selectors for the app icon
            icon_url: str | None = None

            # Method 1: Look for og:image meta tag
            og_image = soup.find("meta", property="og:image")
            if isinstance(og_image, Tag):
                content = og_image.get("content")
                if isinstance(content, str):
                    icon_url = content

            # Method 2: Look for app icon in img tags
            if not icon_url:
                for img in soup.find_all("img"):
                    if not isinstance(img, Tag):
                        continue
                    src = img.get("src", "")
                    if not isinstance(src, str):
                        continue
                    if "icon" in src.lower() or "logo" in src.lower():
                        icon_url = src
                        break

            if not icon_url:
                print("Warning: Could not find icon in Play Store page, using default")
                return None

            # Download the icon
            print(f"Downloading icon from: {icon_url}")
            icon_response = requests.get(icon_url, headers=headers, timeout=10)
            icon_response.raise_for_status()

            # Save to temp file
            temp_icon = self.output_dir / "temp_icon.png"
            temp_icon.write_bytes(icon_response.content)

            return temp_icon

        except Exception as e:
            print(f"Error downloading icon from Play Store: {e}")
            return None

    def _prepare_icon(self) -> None:
        """Prepare app icon from source"""
        icon_source = self.icon_source
        if not icon_source:
            return

        icon_path: Path | None = None

        if icon_source.startswith("http"):
            # It's a URL (likely Play Store)
            icon_path = self._download_playstore_icon(icon_source)
        else:
            # It's a file path
            icon_path = Path(icon_source).expanduser()
            if not icon_path.exists():
                print(f"Warning: Icon file not found: {icon_path}")
                return

        if not icon_path:
            return

        # Create mipmap directories and resize icon
        print("Preparing icon resources...")
        res_dir = self.project_dir / "app" / "src" / "main" / "res"

        icon_sizes = {
            "mipmap-mdpi": 48,
            "mipmap-hdpi": 72,
            "mipmap-xhdpi": 96,
            "mipmap-xxhdpi": 144,
            "mipmap-xxxhdpi": 192,
        }

        try:
            img = Image.open(icon_path)

            for folder, size in icon_sizes.items():
                mipmap_dir = res_dir / folder
                mipmap_dir.mkdir(parents=True, exist_ok=True)

                # Resize and save
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(mipmap_dir / "ic_launcher.png")

            # Clean up temp file if it was downloaded
            if icon_path == self.output_dir / "temp_icon.png":
                icon_path.unlink()

        except Exception as e:
            print(f"Error processing icon: {e}")

    def _create_project_structure(self) -> tuple[Path, Path, Path]:
        """Create the Android project directory structure"""
        print("Creating project structure...")

        # Main directories
        app_src = self.project_dir / "app" / "src" / "main"
        java_dir = app_src / "java" / self.package_name.replace(".", "/")
        res_dir = app_src / "res"

        # Create all necessary directories
        java_dir.mkdir(parents=True, exist_ok=True)
        (res_dir / "layout").mkdir(parents=True, exist_ok=True)
        (res_dir / "values").mkdir(parents=True, exist_ok=True)
        (res_dir / "xml").mkdir(parents=True, exist_ok=True)
        (self.project_dir / "gradle" / "wrapper").mkdir(parents=True, exist_ok=True)

        return app_src, java_dir, res_dir

    def _render_template(self, name: str, **kwargs: str) -> str:
        """Load a template file and substitute {KEY} placeholders"""
        tpl = (Path(__file__).parent / "templates" / name).read_text()
        for key, val in kwargs.items():
            tpl = tpl.replace(f"{{{key}}}", val)
        return tpl

    def _create_resource_files(self, res_dir: Path) -> None:
        """Create required Android resource files"""
        print("Creating resource files...")

        (res_dir / "values" / "strings.xml").write_text(
            self._render_template("strings.xml", APP_NAME=self.app_name)
        )
        (res_dir / "values" / "colors.xml").write_text(self._render_template("colors.xml"))
        (res_dir / "values" / "themes.xml").write_text(self._render_template("themes.xml"))

    def _create_gradle_files(self) -> None:
        """Create Gradle build files"""
        print("Creating Gradle configuration...")

        (self.project_dir / "build.gradle.kts").write_text(
            self._render_template("root_build.gradle.kts")
        )
        (self.project_dir / "app" / "build.gradle.kts").write_text(
            self._render_template("app_build.gradle.kts", PACKAGE_NAME=self.package_name)
        )
        (self.project_dir / "settings.gradle.kts").write_text(
            self._render_template("settings.gradle.kts", APP_NAME=self.app_name)
        )
        (self.project_dir / "gradle.properties").write_text(
            self._render_template("gradle.properties")
        )
        (self.project_dir / "gradle" / "wrapper" / "gradle-wrapper.properties").write_text(
            self._render_template("gradle-wrapper.properties")
        )
        (self.project_dir / "app" / "proguard-rules.pro").write_text(
            "# Add project specific ProGuard rules here\n"
        )

    def _create_android_manifest(self) -> None:
        """Create AndroidManifest.xml"""
        print("Creating Android manifest...")

        manifest_path = self.project_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        manifest_path.write_text(
            self._render_template("AndroidManifest.xml", APP_NAME=self.app_name)
        )

    def _create_main_activity(self, java_dir: Path) -> None:
        """Create MainActivity.kt"""
        print("Creating MainActivity...")

        (java_dir / "MainActivity.kt").write_text(
            self._render_template(
                "MainActivity.kt", PACKAGE_NAME=self.package_name, APP_URL=self.url
            )
        )

    def _create_gradle_wrapper(self) -> bool:
        """Create Gradle wrapper files"""
        print("Creating Gradle wrapper...")

        try:
            templates_dir = Path(__file__).parent / "templates"
            # Create gradlew script for Unix/Mac
            gradlew_script = (templates_dir / "gradlew").read_text()

            # Create gradlew.bat for Windows
            gradlew_bat = (templates_dir / "gradlew.bat").read_text()

            # Write gradlew scripts
            gradlew_path = self.project_dir / "gradlew"
            gradlew_path.write_text(gradlew_script)
            gradlew_path.chmod(0o755)

            gradlew_bat_path = self.project_dir / "gradlew.bat"
            gradlew_bat_path.write_text(gradlew_bat)

            # Download gradle-wrapper.jar from official Gradle distribution
            jar_url = "https://services.gradle.org/distributions/gradle-8.11.1-bin.zip"
            print("Note: gradle-wrapper.jar will be downloaded by Gradle on first build")
            print(f"Or download manually from: {jar_url}")

            jar_path = self.project_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"

            # Try to download the actual wrapper jar from a known good source
            try:
                wrapper_jar_url = "https://raw.githubusercontent.com/gradle/gradle/v8.11.1/gradle/wrapper/gradle-wrapper.jar"
                response = requests.get(wrapper_jar_url, timeout=30)
                response.raise_for_status()
                jar_path.write_bytes(response.content)
                print("Downloaded gradle-wrapper.jar successfully")
            except Exception as jar_error:
                print(f"Warning: Could not download gradle-wrapper.jar: {jar_error}")
                print("You may need to run './gradlew wrapper' manually or install Gradle")
                # Create a note file
                (self.project_dir / "GRADLE_SETUP.txt").write_text(
                    "Gradle wrapper jar could not be downloaded automatically.\n\n"
                    "To fix this, either:\n"
                    "1. Install Gradle locally and run: gradle wrapper\n"
                    "2. Download gradle-8.2-bin.zip from https://services.gradle.org/distributions/\n"
                    "   and extract gradle/wrapper/gradle-wrapper.jar to this project\n"
                )

            return True
        except Exception as e:
            print(f"Error creating Gradle wrapper: {e}")
            return False

    def generate(self) -> Path:
        """Main generation method"""
        print(f"\n{'=' * 60}")
        print(f"Generating WebView App: {self.app_name}")
        print(f"Package: {self.package_name}")
        print(f"URL: {self.url}")
        print(f"{'=' * 60}\n")

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        # Remove existing project if it exists
        if self.project_dir.exists():
            print(f"Removing existing project: {self.project_dir}")
            shutil.rmtree(self.project_dir)

        # Create project structure
        _, java_dir, res_dir = self._create_project_structure()

        # Create all project files
        self._create_gradle_files()
        self._create_resource_files(res_dir)
        self._create_android_manifest()
        self._create_main_activity(java_dir)

        # Prepare icon
        if self.icon_source:
            self._prepare_icon()
        else:
            print("No icon source provided, using default Android icon")

        # Create Gradle wrapper
        if not self._create_gradle_wrapper():
            print("Warning: Failed to create Gradle wrapper, build may fail")

        print(f"\n{'=' * 60}")
        print("Project generated successfully!")
        print(f"Location: {self.project_dir}")
        print(f"{'=' * 60}\n")

        return self.project_dir

    def _build_with_gradle_direct(self) -> Path | None:
        """Build APK directly with Gradle (when already in Docker)"""
        try:
            gradlew = self.project_dir / "gradlew"
            if not gradlew.exists():
                print("Error: gradlew not found")
                return None

            # Set Gradle home environment variable
            build_env = os.environ.copy()
            build_env["GRADLE_USER_HOME"] = str(
                (Path(__file__).parent.parent / ".gradle_cache").absolute()
            )
            build_env["ANDROID_HOME"] = os.environ.get("ANDROID_HOME", "/opt/android-sdk")
            build_env["ANDROID_SDK_ROOT"] = os.environ.get("ANDROID_SDK_ROOT", "/opt/android-sdk")

            print("Running Gradle build (this may take a few minutes on first run)...")
            print("=" * 60)

            # Run gradle build directly
            result = subprocess.run(
                [
                    "./gradlew",
                    "assembleDebug",
                    "--stacktrace",
                    "--warning-mode",
                    "all",
                    "--no-daemon",
                    "--no-watch-fs",
                ],
                cwd=str(self.project_dir.absolute()),
                env=build_env,
                capture_output=False,
            )
            print("=" * 60)

            if result.returncode == 0:
                apk_path = (
                    self.project_dir
                    / "app"
                    / "build"
                    / "outputs"
                    / "apk"
                    / "debug"
                    / "app-debug.apk"
                )
                if apk_path.exists():
                    print("\n" + "=" * 60)
                    print("✓ APK built successfully!")
                    print(f"Location: {apk_path}")
                    print("=" * 60 + "\n")
                    return apk_path
                else:
                    print("\n✗ Error: APK file not found after build")
                    return None
            else:
                print("\n✗ Build failed! Check output above for errors")
                return None

        except Exception as e:
            print(f"Error building APK: {e}")
            traceback.print_exc()
            return None

    def build_apk(self) -> Path | None:
        """Build the APK using Gradle (directly if in Docker, via Docker if not)"""
        print("\n" + "=" * 60)
        print("Building APK...")
        print("=" * 60 + "\n")

        try:
            # Set up shared Gradle cache for all apps in this project
            shared_gradle_cache = Path(__file__).parent.parent / ".gradle_cache"
            shared_gradle_cache.mkdir(exist_ok=True)

            print(f"Using shared Gradle cache: {shared_gradle_cache}")

            # Check if we're already running inside Docker
            in_docker = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "true"

            if in_docker:
                # We're already in Docker, run Gradle directly
                print("Running in Docker container, building directly...")
                return self._build_with_gradle_direct()

            # Check if Docker is available on host
            try:
                subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    check=True,
                )
            except (subprocess.SubprocessError, FileNotFoundError):
                print("Error: Docker is not installed or not running")
                print("Please install Docker: https://docs.docker.com/get-docker/")
                return None

            # Build Docker image if it doesn't exist
            print("Checking Docker image...")
            docker_image = "webview-generator-builder"
            dockerfile_path = Path(__file__).parent / "Dockerfile"

            # Check if image exists
            images_result = subprocess.run(
                ["docker", "images", "-q", docker_image],
                capture_output=True,
                text=True,
            )

            if not images_result.stdout.strip():
                print("Building Docker image (this will take a few minutes on first run)...")
                print("=" * 60)
                build_result = subprocess.run(
                    [
                        "docker",
                        "build",
                        "--platform",
                        "linux/amd64",
                        "-t",
                        docker_image,
                        "-f",
                        str(dockerfile_path),
                        str(Path(__file__).parent.parent),
                    ]
                )
                print("=" * 60)
                if build_result.returncode != 0:
                    print("Failed to build Docker image")
                    return None
                print("Docker image built successfully")

            # Run build in Docker container
            print("\nRunning Gradle build in Docker (this may take a few minutes on first run)...")
            print("=" * 60)

            # Run docker build with live output (force linux/amd64 for AAPT2 compatibility)
            run_result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--platform",
                    "linux/amd64",
                    "-e",
                    "GRADLE_USER_HOME=/gradle_cache",
                    "-v",
                    f"{self.project_dir.absolute()}:/project",
                    "-v",
                    f"{shared_gradle_cache.absolute()}:/gradle_cache",
                    "-w",
                    "/project",
                    docker_image,
                    "./gradlew",
                    "assembleDebug",
                    "--stacktrace",
                    "--no-daemon",
                    "--no-watch-fs",
                ]
            )
            print("=" * 60)

            if run_result.returncode == 0:
                apk_path = (
                    self.project_dir
                    / "app"
                    / "build"
                    / "outputs"
                    / "apk"
                    / "debug"
                    / "app-debug.apk"
                )
                if apk_path.exists():
                    print("\n" + "=" * 60)
                    print("✓ APK built successfully!")
                    print(f"Location: {apk_path}")
                    print("=" * 60 + "\n")
                    return apk_path
                else:
                    print("\n✗ Error: APK file not found after build")
                    return None
            else:
                print("\n✗ Build failed! Check output above for errors")
                return None

        except Exception as e:
            print(f"Error building APK: {e}")
            return None

    def install_apk(self, apk_path: Path | None) -> bool:
        """Install APK on connected device using adb"""
        if not apk_path or not apk_path.exists():
            print("Error: APK not found")
            return False

        try:
            print("\n" + "=" * 60)
            print("Installing APK on device...")
            print("=" * 60 + "\n")

            # Uninstall existing app (ignore errors if not installed)
            print(f"Uninstalling existing app: {self.package_name}")
            subprocess.run(
                ["adb", "uninstall", self.package_name],
                capture_output=True,
            )

            # Install APK
            print(f"Installing APK: {apk_path}")
            result = subprocess.run(
                ["adb", "install", str(apk_path)],
                capture_output=False,
            )

            if result.returncode != 0:
                print("\n✗ Installation failed!")
                return False

            # Launch app
            print(f"Launching app: {self.package_name}")
            subprocess.run(
                ["adb", "shell", "monkey", "-p", self.package_name, "1"],
                capture_output=True,
            )

            print("\n" + "=" * 60)
            print("✓ APK installed and launched successfully!")
            print("=" * 60 + "\n")
            return True

        except FileNotFoundError:
            print("Error: adb not found. Please install Android SDK platform-tools")
            return False
        except Exception as e:
            print(f"Error installing APK: {e}")
            return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a WebView-based Android app from a URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url https://example.com --name "My App" --icon icon.png
  %(prog)s --url https://example.com --name "My App" --icon https://play.google.com/store/apps/details?id=com.example
  %(prog)s --url https://example.com --name "My App" --build
        """,
    )

    parser.add_argument("--url", required=True, help="URL to load in the WebView")
    parser.add_argument("--name", required=True, help="App name")
    parser.add_argument("--icon", help="Path to icon file or Play Store URL")
    parser.add_argument("--output", default="output", help="Output directory (default: output)")
    parser.add_argument("--build", action="store_true", help="Build APK after generation")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install APK on device after build (implies --build)",
    )
    parser.add_argument("--package", help="Custom package name (default: auto-generated)")

    args = parser.parse_args()

    # Validate URL
    try:
        parsed = urlparse(args.url)
        if not parsed.scheme or not parsed.netloc:
            print("Error: Invalid URL provided")
            sys.exit(1)
    except Exception:
        print("Error: Invalid URL provided")
        sys.exit(1)

    # Create generator
    generator = WebViewAppGenerator(
        url=args.url,
        app_name=args.name,
        icon_source=args.icon,
        output_dir=args.output,
    )

    # Override package name if provided
    if args.package:
        generator.package_name = args.package

    # Generate project
    try:
        project_dir = generator.generate()

        # Build if requested (or if install is requested)
        if args.build or args.install:
            apk_path = generator.build_apk()

            # Install if requested (only when not in Docker - build.sh handles install on host)
            in_docker = os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "true"
            if args.install and apk_path and not in_docker:
                generator.install_apk(apk_path)
        else:
            print("\nTo build the APK, run:")
            print(f"  cd {project_dir}")
            print("  ./gradlew assembleDebug")
            print("\nOr run this script with --build flag")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
