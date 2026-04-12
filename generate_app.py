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
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image


class WebViewAppGenerator:
    def __init__(self, url, app_name, icon_source, output_dir="output"):
        self.url = url
        self.app_name = app_name
        self.package_name = self._generate_package_name(app_name)
        self.icon_source = icon_source
        self.output_dir = Path(output_dir)
        self.project_dir = self.output_dir / self._sanitize_filename(app_name)

    def _sanitize_filename(self, name):
        """Convert app name to a valid directory name"""
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

    def _generate_package_name(self, app_name):
        """Generate package name from app name"""
        # Convert to lowercase, remove special chars, replace spaces with dots
        clean_name = re.sub(r'[^\w\s]', '', app_name.lower())
        clean_name = re.sub(r'\s+', '.', clean_name.strip())
        return f"com.webview.{clean_name}"

    def _download_playstore_icon(self, playstore_url):
        """Download app icon from Play Store URL"""
        # Clean up URL - remove any shell escape characters
        playstore_url = playstore_url.replace('\\', '')

        print(f"Fetching icon from Play Store: {playstore_url}")

        try:
            # Fetch the Play Store page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(playstore_url, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML to find icon
            soup = BeautifulSoup(response.text, 'lxml')

            # Try multiple selectors for the app icon
            icon_url = None

            # Method 1: Look for og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                icon_url = og_image['content']

            # Method 2: Look for app icon in img tags
            if not icon_url:
                for img in soup.find_all('img'):
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    if 'icon' in src.lower() or 'logo' in src.lower():
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

    def _prepare_icon(self):
        """Prepare app icon from source"""
        icon_path = None

        if self.icon_source.startswith('http'):
            # It's a URL (likely Play Store)
            icon_path = self._download_playstore_icon(self.icon_source)
        else:
            # It's a file path
            icon_path = Path(self.icon_source)
            if not icon_path.exists():
                print(f"Warning: Icon file not found: {icon_path}")
                return None

        if not icon_path:
            return None

        # Create mipmap directories and resize icon
        print("Preparing icon resources...")
        res_dir = self.project_dir / "app" / "src" / "main" / "res"

        icon_sizes = {
            'mipmap-mdpi': 48,
            'mipmap-hdpi': 72,
            'mipmap-xhdpi': 96,
            'mipmap-xxhdpi': 144,
            'mipmap-xxxhdpi': 192
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

            return True

        except Exception as e:
            print(f"Error processing icon: {e}")
            return None

    def _create_project_structure(self):
        """Create the Android project directory structure"""
        print("Creating project structure...")

        # Main directories
        app_src = self.project_dir / "app" / "src" / "main"
        java_dir = app_src / "java" / self.package_name.replace('.', '/')
        res_dir = app_src / "res"

        # Create all necessary directories
        java_dir.mkdir(parents=True, exist_ok=True)
        (res_dir / "layout").mkdir(parents=True, exist_ok=True)
        (res_dir / "values").mkdir(parents=True, exist_ok=True)
        (res_dir / "xml").mkdir(parents=True, exist_ok=True)
        (self.project_dir / "gradle" / "wrapper").mkdir(parents=True, exist_ok=True)

        return app_src, java_dir, res_dir

    def _create_resource_files(self, res_dir):
        """Create required Android resource files"""
        print("Creating resource files...")

        # strings.xml
        strings_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{self.app_name}</string>
</resources>
'''

        # colors.xml
        colors_xml = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="colorPrimary">#6200EE</color>
    <color name="colorPrimaryDark">#3700B3</color>
    <color name="colorAccent">#03DAC5</color>
</resources>
'''

        # themes.xml
        themes_xml = '''<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:tools="http://schemas.android.com/tools">
    <style name="AppTheme" parent="Theme.Material3.Light.NoActionBar">
        <item name="colorPrimary">@color/colorPrimary</item>
        <item name="colorPrimaryDark">@color/colorPrimaryDark</item>
        <item name="colorAccent">@color/colorAccent</item>
        <!-- Opt out of Android 15 enforced edge-to-edge -->
        <item name="android:windowOptOutEdgeToEdgeEnforcement" tools:targetApi="35">true</item>
    </style>
</resources>
'''

        # Write files
        (res_dir / "values" / "strings.xml").write_text(strings_xml)
        (res_dir / "values" / "colors.xml").write_text(colors_xml)
        (res_dir / "values" / "themes.xml").write_text(themes_xml)

    def _create_gradle_files(self):
        """Create Gradle build files"""
        print("Creating Gradle configuration...")

        # Root build.gradle.kts (Kotlin DSL)
        root_build_gradle = f'''// Top-level build file
plugins {{
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
}}

tasks.register<Delete>("clean") {{
    delete(rootProject.layout.buildDirectory)
}}
'''

        # App build.gradle.kts (Kotlin DSL)
        app_build_gradle = f'''plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}

android {{
    namespace = "{self.package_name}"
    compileSdk = 35

    defaultConfig {{
        applicationId = "{self.package_name}"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
    }}

    buildTypes {{
        release {{
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }}
    }}

    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}

    kotlinOptions {{
        jvmTarget = "17"
    }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.webkit:webkit:1.12.1")
}}
'''

        # settings.gradle.kts (Kotlin DSL)
        settings_gradle = f'''pluginManagement {{
    repositories {{
        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}

dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
        google()
        mavenCentral()
    }}
}}

rootProject.name = "{self.app_name}"
include(":app")
'''

        # gradle.properties
        gradle_properties = '''org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.enableJetifier=true
kotlin.code.style=official
'''

        # gradle-wrapper.properties
        wrapper_properties = '''distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-8.11.1-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
'''

        # Write files (using .kts extension for Kotlin DSL)
        (self.project_dir / "build.gradle.kts").write_text(root_build_gradle)
        (self.project_dir / "app" / "build.gradle.kts").write_text(app_build_gradle)
        (self.project_dir / "settings.gradle.kts").write_text(settings_gradle)
        (self.project_dir / "gradle.properties").write_text(gradle_properties)
        (self.project_dir / "gradle" / "wrapper" / "gradle-wrapper.properties").write_text(wrapper_properties)
        (self.project_dir / "app" / "proguard-rules.pro").write_text("# Add project specific ProGuard rules here\n")

    def _create_android_manifest(self):
        """Create AndroidManifest.xml"""
        print("Creating Android manifest...")

        manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />

    <!-- Disable safe browsing globally -->
    <meta-data android:name="android.webkit.WebView.EnableSafeBrowsing"
        android:value="false" />

    <application
        android:allowBackup="true"
        android:hardwareAccelerated="true"
        android:icon="@mipmap/ic_launcher"
        android:label="{self.app_name}"
        android:supportsRtl="true"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize"
            android:configChanges="orientation|screenSize|smallestScreenSize|density|screenLayout|uiMode|keyboard|keyboardHidden|navigation">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
'''

        manifest_path = self.project_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        manifest_path.write_text(manifest)

    def _create_main_activity(self, java_dir):
        """Create MainActivity.kt"""
        print("Creating MainActivity...")

        activity_code = f'''package {self.package_name}

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.*
import android.widget.FrameLayout
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature

class MainActivity : AppCompatActivity() {{

    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private val FILE_CHOOSER_REQUEST_CODE = 1

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)

        // Create layout programmatically
        val container = FrameLayout(this)
        webView = WebView(this)

        webView.isFocusable = true
        webView.isFocusableInTouchMode = true
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {{
            webView.isForceDarkAllowed = false
        }}

        container.addView(webView, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        ))
        setContentView(container)

        // Remove "wv" from user agent to prevent WebView detection
        val defaultUA = webView.settings.userAgentString
        webView.settings.userAgentString = defaultUA.replace("; wv", "")

        webView.webViewClient = object : WebViewClient() {{
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {{
                val url = request?.url.toString()

                // Handle external links
                if (url.startsWith("http://") || url.startsWith("https://")) {{
                    return false // Load in WebView
                }}

                // Handle other schemes (tel:, mailto:, etc.)
                try {{
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    return true
                }} catch (e: Exception) {{
                    Toast.makeText(this@MainActivity, "Cannot open link", Toast.LENGTH_SHORT).show()
                    return true
                }}
            }}

            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {{
                super.onPageStarted(view, url, favicon)
                // Inject visibilitychange blocking as early as possible
                view?.evaluateJavascript("document.addEventListener(\\"visibilitychange\\",function (event) {{event.stopImmediatePropagation();}},true);", null)
            }}

            override fun onPageFinished(view: WebView?, url: String?) {{
                super.onPageFinished(view, url)
                // Page finished loading

                // Stop visibilitychange event propagation
                view?.evaluateJavascript("document.addEventListener(\\"visibilitychange\\",function (event) {{event.stopImmediatePropagation();}},true);", null)

                // FIX: dvh (dynamic viewport height) CSS unit resolves to 0 in some WebView configs.
                // Inject CSS to make dvh fall back to vh for any element using it.
                view?.evaluateJavascript("""
                    (function() {{
                        if (!document.getElementById('dvh-fix')) {{
                            var style = document.createElement('style');
                            style.id = 'dvh-fix';
                            style.textContent = '*, *::before, *::after {{ --dvh-fix: 1vh; }} [class*="h-dvh"] {{ height: 100vh !important; }} [class*="min-h-dvh"] {{ min-height: 100vh !important; }} [class*="max-h-dvh"] {{ max-height: 100vh !important; }}';
                            document.head.appendChild(style);
                        }}
                    }})()
                """.trimIndent(), null)

            }}

            override fun onLoadResource(view: WebView?, url: String?) {{
                super.onLoadResource(view, url)
                // Also inject visibilitychange blocking in onLoadResource
                view?.evaluateJavascript("document.addEventListener(\\"visibilitychange\\", (event) => {{ event.stopImmediatePropagation(); }}, true);", null)
            }}

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {{
                super.onReceivedError(view, request, error)
                // Only show error for main frame failures
                if (request?.isForMainFrame == true) {{
                    Toast.makeText(
                        this@MainActivity,
                        "Page load error: ${{error?.description ?: "Unknown error"}}",
                        Toast.LENGTH_LONG
                    ).show()
                }}
            }}
        }}

        // Set WebChromeClient for file upload support and loading progress
        webView.webChromeClient = object : WebChromeClient() {{
            override fun onProgressChanged(view: WebView?, newProgress: Int) {{
                super.onProgressChanged(view, newProgress)
                // Show loading progress
                // Progress: newProgress
            }}

            override fun onShowCustomView(view: android.view.View?, callback: CustomViewCallback?) {{
                super.onShowCustomView(view, callback)
            }}

            override fun onCreateWindow(view: WebView?, isDialog: Boolean, isUserGesture: Boolean, resultMsg: android.os.Message?): Boolean {{
                return false
            }}

            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {{
                this@MainActivity.filePathCallback?.onReceiveValue(null)
                this@MainActivity.filePathCallback = filePathCallback

                val intent = fileChooserParams?.createIntent()
                if (intent == null) {{
                    this@MainActivity.filePathCallback = null
                    Toast.makeText(this@MainActivity, "Cannot open file chooser", Toast.LENGTH_SHORT).show()
                    return false
                }}

                try {{
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST_CODE)
                }} catch (e: Exception) {{
                    this@MainActivity.filePathCallback = null
                    Toast.makeText(this@MainActivity, "Cannot open file chooser", Toast.LENGTH_SHORT).show()
                    return false
                }}
                return true
            }}
        }}

        // Configure WebView settings
        webView.settings.apply {{
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {{
                safeBrowsingEnabled = false
            }}
            setDomStorageEnabled(true)
            databaseEnabled = true
            setAllowFileAccess(true)
            setBlockNetworkLoads(false)
            javaScriptEnabled = true
        }}

        // Disable X-Requested-With header to prevent WebView detection
        try {{
            if (WebViewFeature.isFeatureSupported(WebViewFeature.REQUESTED_WITH_HEADER_ALLOW_LIST)) {{
                WebSettingsCompat.setRequestedWithHeaderOriginAllowList(
                    webView.settings,
                    emptySet()
                )
            }}
        }} catch (_: Exception) {{}}

        // Enable persistent cookies and storage
        android.webkit.CookieManager.getInstance().apply {{
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, true)
        }}

        // Custom headers to prevent WebView detection
        val customHeaders = mapOf(
            "X-Requested-With" to "",
            "DNT" to "1"
        )

        webView.loadUrl("{self.url}", customHeaders)
    }}

    override fun onResume() {{
        super.onResume()
        webView.onResume()
        webView.resumeTimers()
    }}

    override fun onPause() {{
        webView.evaluateJavascript("document.querySelectorAll('audio').forEach(x => x.pause());document.querySelectorAll('video').forEach(x => x.pause());", null)
        android.webkit.CookieManager.getInstance().flush()
        webView.onPause()
        webView.pauseTimers()
        super.onPause()
    }}

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {{
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {{
            val results = if (resultCode == Activity.RESULT_OK && data != null) {{
                arrayOf(Uri.parse(data.dataString))
            }} else {{
                null
            }}
            filePathCallback?.onReceiveValue(results)
            filePathCallback = null
        }}
    }}
}}
'''

        (java_dir / "MainActivity.kt").write_text(activity_code)

    def _create_gradle_wrapper(self):
        """Create Gradle wrapper files"""
        print("Creating Gradle wrapper...")

        try:
            # Create gradlew script for Unix/Mac
            gradlew_script = '''#!/bin/sh

#
# Copyright © 2015-2021 the original authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

##############################################################################
#
#   Gradle start up script for POSIX generated by Gradle.
#
#   Important for running:
#
#   (1) You need a POSIX-compliant shell to run this script. If your /bin/sh is
#       noncompliant, but you have some other compliant shell such as ksh or
#       bash, then to run this script, type that shell name before the whole
#       command line, like:
#
#           ksh Gradle
#
#       Busybox and similar reduced shells will NOT work, because this script
#       requires all of these POSIX shell features:
#         * functions;
#         * expansions «$var», «${var}», «${var:-default}», «${var+SET}»,
#           «${var#prefix}», «${var%suffix}», and «$( cmd )»;
#         * compound commands having a testable exit status, especially «case»;
#         * various built-in commands including «command», «set», and «ulimit».
#
#   Important for patching:
#
#   (2) This script targets any POSIX shell, so it avoids extensions provided
#       by Bash, Ksh, etc; in particular arrays are avoided.
#
#       The "traditional" practice of packing multiple parameters into a
#       space-separated string is a well documented source of bugs and security
#       problems, so this is (mostly) avoided, by progressively accumulating
#       options in "$@", and eventually passing that to Java.
#
#       Where the inherited environment variables (DEFAULT_JVM_OPTS, JAVA_OPTS,
#       and GRADLE_OPTS) rely on word-splitting, this is performed explicitly;
#       see the in-line comments for details.
#
#       There are tweaks for specific operating systems such as AIX, CygWin,
#       Darwin, MinGW, and NonStop.
#
#   (3) This script is generated from the Groovy template
#       https://github.com/gradle/gradle/blob/HEAD/subprojects/plugins/src/main/resources/org/gradle/api/internal/plugins/unixStartScript.txt
#       within the Gradle project.
#
#       You can find Gradle at https://github.com/gradle/gradle/.
#
##############################################################################

# Attempt to set APP_HOME

# Resolve links: $0 may be a link
app_path=$0

# Need this for daisy-chained symlinks.
while
    APP_HOME=${app_path%"${app_path##*/}"}  # leaves a trailing /; empty if no leading path
    [ -h "$app_path" ]
do
    ls=$( ls -ld "$app_path" )
    link=${ls#*' -> '}
    case $link in             #(
      /*)   app_path=$link ;; #(
      *)    app_path=$APP_HOME$link ;;
    esac
done

# This is normally unused
# shellcheck disable=SC2034
APP_BASE_NAME=${0##*/}
APP_HOME=$( cd "${APP_HOME:-./}" && pwd -P ) || exit

# Use the maximum available, or set MAX_FD != -1 to use that value.
MAX_FD=maximum

warn () {
    echo "$*"
} >&2

die () {
    echo
    echo "$*"
    echo
    exit 1
} >&2

# OS specific support (must be 'true' or 'false').
cygwin=false
msys=false
darwin=false
nonstop=false
case "$( uname )" in                #(
  CYGWIN* )         cygwin=true  ;; #(
  Darwin* )         darwin=true  ;; #(
  MSYS* | MINGW* )  msys=true    ;; #(
  NONSTOP* )        nonstop=true ;;
esac

CLASSPATH=$APP_HOME/gradle/wrapper/gradle-wrapper.jar


# Determine the Java command to use to start the JVM.
if [ -n "$JAVA_HOME" ] ; then
    if [ -x "$JAVA_HOME/jre/sh/java" ] ; then
        # IBM's JDK on AIX uses strange locations for the executables
        JAVACMD=$JAVA_HOME/jre/sh/java
    else
        JAVACMD=$JAVA_HOME/bin/java
    fi
    if [ ! -x "$JAVACMD" ] ; then
        die "ERROR: JAVA_HOME is set to an invalid directory: $JAVA_HOME

Please set the JAVA_HOME variable in your environment to match the
location of your Java installation."
    fi
else
    JAVACMD=java
    which java >/dev/null 2>&1 || die "ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.

Please set the JAVA_HOME variable in your environment to match the
location of your Java installation."
fi

# Increase the maximum file descriptors if we can.
if ! "$cygwin" && ! "$darwin" && ! "$nonstop" ; then
    case $MAX_FD in #(
      max*)
        # In POSIX sh, ulimit -H is undefined. That's why the result is checked to see if it worked.
        # shellcheck disable=SC3045
        MAX_FD=$( ulimit -H -n ) ||
            warn "Could not query maximum file descriptor limit"
    esac
    case $MAX_FD in  #(
      '' | soft) :;; #(
      *)
        # In POSIX sh, ulimit -n is undefined. That's why the result is checked to see if it worked.
        # shellcheck disable=SC3045
        ulimit -n "$MAX_FD" ||
            warn "Could not set maximum file descriptor limit to $MAX_FD"
    esac
fi

# Collect all arguments for the java command, stacking in reverse order:
#   * args from the command line
#   * the main class name
#   * -classpath
#   * -D...appname settings
#   * --module-path (only if needed)
#   * DEFAULT_JVM_OPTS, JAVA_OPTS, and GRADLE_OPTS environment variables.

# For Cygwin or MSYS, switch paths to Windows format before running java
if "$cygwin" || "$msys" ; then
    APP_HOME=$( cygpath --path --mixed "$APP_HOME" )
    CLASSPATH=$( cygpath --path --mixed "$CLASSPATH" )

    JAVACMD=$( cygpath --unix "$JAVACMD" )

    # Now convert the arguments - kludge to limit ourselves to /bin/sh
    for arg do
        if
            case $arg in                                #(
              -*)   false ;;                            # don't mess with options #(
              /?*)  t=${arg#/} t=/${t%%/*}              # looks like a POSIX filepath
                    [ -e "$t" ] ;;                      #(
              *)    false ;;
            esac
        then
            arg=$( cygpath --path --ignore --mixed "$arg" )
        fi
        # Roll the args list around exactly as many times as the number of
        # args, so each arg winds up back in the position where it started, but
        # possibly modified.
        #
        # NB: a `for` loop captures its iteration list before it begins, so
        # changing the positional parameters here affects neither the number of
        # iterations, nor the values presented in `arg`.
        shift                   # remove old arg
        set -- "$@" "$arg"      # push replacement arg
    done
fi


# Add default JVM options here. You can also use JAVA_OPTS and GRADLE_OPTS to pass JVM options to this script.
DEFAULT_JVM_OPTS='"-Xmx64m" "-Xms64m"'

# Collect all arguments for the java command;
#   * $DEFAULT_JVM_OPTS, $JAVA_OPTS, and $GRADLE_OPTS can contain fragments of
#     shell script including quotes and variable substitutions, so put them in
#     double quotes to make sure that they get re-expanded; and
#   * put everything else in single quotes, so that it's not re-expanded.

set -- \\
        "-Dorg.gradle.appname=$APP_BASE_NAME" \\
        -classpath "$CLASSPATH" \\
        org.gradle.wrapper.GradleWrapperMain \\
        "$@"

# Stop when "xargs" is not available.
if ! command -v xargs >/dev/null 2>&1
then
    die "xargs is not available"
fi

# Use "xargs" to parse quoted args.
#
# With -n1 it outputs one arg per line, with the quotes and backslashes removed.
#
# In Bash we could simply go:
#
#   readarray ARGS < <( xargs -n1 <<<"$var" ) &&
#   set -- "${ARGS[@]}" "$@"
#
# but POSIX shell has neither arrays nor command substitution, so instead we
# post-process each arg (as a line of input to sed) to backslash-escape any
# character that might be a shell metacharacter, then use eval to reverse
# that process (while maintaining the separation between arguments), and wrap
# the whole thing up as a single "set" statement.
#
# This will of course break if any of these variables contains a newline or
# an unmatched quote.
#

eval "set -- $(
        printf '%s\\n' "$DEFAULT_JVM_OPTS $JAVA_OPTS $GRADLE_OPTS" |
        xargs -n1 |
        sed ' s~[^-[:alnum:]+,./:=@_]~\\\\&~g; ' |
        tr '\\n' ' '
    )" '"$@"'

exec "$JAVACMD" "$@"
'''

            # Create gradlew.bat for Windows
            gradlew_bat = '''@rem
@rem Copyright 2015 the original author or authors.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem      https://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.
@rem

@if "%DEBUG%"=="" @echo off
@rem ##########################################################################
@rem
@rem  Gradle startup script for Windows
@rem
@rem ##########################################################################

@rem Set local scope for the variables with windows NT shell
if "%OS%"=="Windows_NT" setlocal

set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.
@rem This is normally unused
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%

@rem Resolve any "." and ".." in APP_HOME to make it shorter.
for %%i in ("%APP_HOME%") do set APP_HOME=%%~fi

@rem Add default JVM options here. You can also use JAVA_OPTS and GRADLE_OPTS to pass JVM options to this script.
set DEFAULT_JVM_OPTS="-Xmx64m" "-Xms64m"

@rem Find java.exe
if defined JAVA_HOME goto findJavaFromJavaHome

set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if %ERRORLEVEL% equ 0 goto execute

echo.
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe

if exist "%JAVA_EXE%" goto execute

echo.
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME%
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:execute
@rem Setup the command line

set CLASSPATH=%APP_HOME%\\gradle\\wrapper\\gradle-wrapper.jar


@rem Execute Gradle
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %GRADLE_OPTS% "-Dorg.gradle.appname=%APP_BASE_NAME%" -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*

:end
@rem End local scope for the variables with windows NT shell
if %ERRORLEVEL% equ 0 goto mainEnd

:fail
rem Set variable GRADLE_EXIT_CONSOLE if you need the _script_ return code instead of
rem the _cmd.exe /c_ return code!
set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% equ 0 set EXIT_CODE=1
if not ""=="%GRADLE_EXIT_CONSOLE%" exit %EXIT_CODE%
exit /b %EXIT_CODE%

:mainEnd
if "%OS%"=="Windows_NT" endlocal

:omega
'''

            # Write gradlew scripts
            gradlew_path = self.project_dir / "gradlew"
            gradlew_path.write_text(gradlew_script)
            gradlew_path.chmod(0o755)

            gradlew_bat_path = self.project_dir / "gradlew.bat"
            gradlew_bat_path.write_text(gradlew_bat)

            # Download gradle-wrapper.jar from official Gradle distribution
            jar_url = "https://services.gradle.org/distributions/gradle-8.11.1-bin.zip"
            print(f"Note: gradle-wrapper.jar will be downloaded by Gradle on first build")
            print(f"Or download manually from: {jar_url}")

            # Create a minimal gradle-wrapper.jar placeholder or download it
            # For now, we'll let Gradle download it on first run
            # Create empty jar as placeholder
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

    def generate(self):
        """Main generation method"""
        print(f"\n{'='*60}")
        print(f"Generating WebView App: {self.app_name}")
        print(f"Package: {self.package_name}")
        print(f"URL: {self.url}")
        print(f"{'='*60}\n")

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        # Remove existing project if it exists
        if self.project_dir.exists():
            print(f"Removing existing project: {self.project_dir}")
            shutil.rmtree(self.project_dir)

        # Create project structure
        app_src, java_dir, res_dir = self._create_project_structure()

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

        print(f"\n{'='*60}")
        print(f"Project generated successfully!")
        print(f"Location: {self.project_dir}")
        print(f"{'='*60}\n")

        return self.project_dir

    def _build_with_gradle_direct(self):
        """Build APK directly with Gradle (when already in Docker)"""
        try:
            gradlew = self.project_dir / "gradlew"
            if not gradlew.exists():
                print("Error: gradlew not found")
                return None

            # Set Gradle home environment variable
            build_env = os.environ.copy()
            build_env['GRADLE_USER_HOME'] = str((Path(__file__).parent / ".gradle_cache").absolute())
            build_env['ANDROID_HOME'] = os.environ.get('ANDROID_HOME', '/opt/android-sdk')
            build_env['ANDROID_SDK_ROOT'] = os.environ.get('ANDROID_SDK_ROOT', '/opt/android-sdk')

            print("Running Gradle build (this may take a few minutes on first run)...")
            print("="*60)

            # Run gradle build directly
            result = subprocess.run(
                ["./gradlew", "assembleDebug", "--stacktrace", "--warning-mode", "all", "--no-daemon", "--no-watch-fs"],
                cwd=str(self.project_dir.absolute()),
                env=build_env,
                capture_output=False
            )
            print("="*60)

            if result.returncode == 0:
                apk_path = self.project_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
                if apk_path.exists():
                    print("\n" + "="*60)
                    print(f"✓ APK built successfully!")
                    print(f"Location: {apk_path}")
                    print("="*60 + "\n")
                    return apk_path
                else:
                    print("\n✗ Error: APK file not found after build")
                    return None
            else:
                print("\n✗ Build failed! Check output above for errors")
                return None

        except Exception as e:
            print(f"Error building APK: {e}")
            import traceback
            traceback.print_exc()
            return None

    def build_apk(self):
        """Build the APK using Gradle (directly if in Docker, via Docker if not)"""
        print("\n" + "="*60)
        print("Building APK...")
        print("="*60 + "\n")

        try:
            # Set up shared Gradle cache for all apps in this project
            shared_gradle_cache = Path(__file__).parent / ".gradle_cache"
            shared_gradle_cache.mkdir(exist_ok=True)

            print(f"Using shared Gradle cache: {shared_gradle_cache}")

            # Check if we're already running inside Docker
            in_docker = os.path.exists('/.dockerenv') or os.environ.get('IN_DOCKER') == 'true'

            if in_docker:
                # We're already in Docker, run Gradle directly
                print("Running in Docker container, building directly...")
                return self._build_with_gradle_direct()

            # Check if Docker is available on host
            try:
                subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    check=True
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
            result = subprocess.run(
                ["docker", "images", "-q", docker_image],
                capture_output=True,
                text=True
            )

            if not result.stdout.strip():
                print("Building Docker image (this will take a few minutes on first run)...")
                print("="*60)
                build_result = subprocess.run(
                    ["docker", "build", "--platform", "linux/amd64", "-t", docker_image, "-f", str(dockerfile_path), str(Path(__file__).parent)]
                )
                print("="*60)
                if build_result.returncode != 0:
                    print("Failed to build Docker image")
                    return None
                print("Docker image built successfully")

            # Run build in Docker container
            print("\nRunning Gradle build in Docker (this may take a few minutes on first run)...")
            print("="*60)

            # Run docker build with live output (force linux/amd64 for AAPT2 compatibility)
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "--platform", "linux/amd64",
                    "-e", f"GRADLE_USER_HOME=/gradle_cache",
                    "-v", f"{self.project_dir.absolute()}:/project",
                    "-v", f"{shared_gradle_cache.absolute()}:/gradle_cache",
                    "-w", "/project",
                    docker_image,
                    "./gradlew", "assembleDebug", "--stacktrace", "--no-daemon", "--no-watch-fs"
                ]
            )
            print("="*60)

            if result.returncode == 0:
                apk_path = self.project_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
                if apk_path.exists():
                    print("\n" + "="*60)
                    print(f"✓ APK built successfully!")
                    print(f"Location: {apk_path}")
                    print("="*60 + "\n")
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

    def install_apk(self, apk_path):
        """Install APK on connected device using adb"""
        if not apk_path or not Path(apk_path).exists():
            print("Error: APK not found")
            return False

        try:
            print("\n" + "="*60)
            print("Installing APK on device...")
            print("="*60 + "\n")

            # Uninstall existing app (ignore errors if not installed)
            print(f"Uninstalling existing app: {self.package_name}")
            subprocess.run(
                ["adb", "uninstall", self.package_name],
                capture_output=True
            )

            # Install APK
            print(f"Installing APK: {apk_path}")
            result = subprocess.run(
                ["adb", "install", str(apk_path)],
                capture_output=False
            )

            if result.returncode != 0:
                print("\n✗ Installation failed!")
                return False

            # Launch app
            print(f"Launching app: {self.package_name}")
            subprocess.run(
                ["adb", "shell", "monkey", "-p", self.package_name, "1"],
                capture_output=True
            )

            print("\n" + "="*60)
            print("✓ APK installed and launched successfully!")
            print("="*60 + "\n")
            return True

        except FileNotFoundError:
            print("Error: adb not found. Please install Android SDK platform-tools")
            return False
        except Exception as e:
            print(f"Error installing APK: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate a WebView-based Android app from a URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --url https://example.com --name "My App" --icon icon.png
  %(prog)s --url https://example.com --name "My App" --icon https://play.google.com/store/apps/details?id=com.example
  %(prog)s --url https://example.com --name "My App" --build
        '''
    )

    parser.add_argument('--url', required=True, help='URL to load in the WebView')
    parser.add_argument('--name', required=True, help='App name')
    parser.add_argument('--icon', help='Path to icon file or Play Store URL')
    parser.add_argument('--output', default='output', help='Output directory (default: output)')
    parser.add_argument('--build', action='store_true', help='Build APK after generation')
    parser.add_argument('--install', action='store_true', help='Install APK on device after build (implies --build)')
    parser.add_argument('--package', help='Custom package name (default: auto-generated)')

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
        output_dir=args.output
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
            in_docker = os.path.exists('/.dockerenv') or os.environ.get('IN_DOCKER') == 'true'
            if args.install and apk_path and not in_docker:
                generator.install_apk(apk_path)
        else:
            print("\nTo build the APK, run:")
            print(f"  cd {project_dir}")
            print(f"  ./gradlew assembleDebug")
            print(f"\nOr run this script with --build flag")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
