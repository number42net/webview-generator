import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from generate_app import WebViewAppGenerator


def make_gen(
    tmp_path: Path,
    app_name: str = "My App",
    url: str = "https://example.com",
) -> WebViewAppGenerator:
    return WebViewAppGenerator(
        url=url,
        app_name=app_name,
        icon_source=None,
        output_dir=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# _sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_spaces_become_underscores(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="My App")
        assert g._sanitize_filename("My App") == "My_App"

    def test_special_chars_removed(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        # trailing spaces are stripped before space→underscore, so no trailing underscore
        assert g._sanitize_filename("App! @#$") == "App"

    def test_hyphens_preserved(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._sanitize_filename("My-App") == "My-App"

    def test_already_clean(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._sanitize_filename("MyApp") == "MyApp"


# ---------------------------------------------------------------------------
# _generate_package_name
# ---------------------------------------------------------------------------


class TestGeneratePackageName:
    def test_basic(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._generate_package_name("My App") == "com.webview.my.app"

    def test_uppercase_lowered(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._generate_package_name("Twitter") == "com.webview.twitter"

    def test_special_chars_stripped(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._generate_package_name("My App!") == "com.webview.my.app"

    def test_multiple_spaces_collapsed(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._generate_package_name("My  App") == "com.webview.my.app"

    def test_prefix_always_present(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        assert g._generate_package_name("Foo").startswith("com.webview.")


# ---------------------------------------------------------------------------
# _render_template
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    def test_substitution(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        result = g._render_template("strings.xml", APP_NAME="Test App")
        assert "Test App" in result
        assert "{APP_NAME}" not in result

    def test_unset_placeholder_left_intact(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        # strings.xml has {APP_NAME}; if we don't pass it, it stays
        result = g._render_template("strings.xml")
        assert "{APP_NAME}" in result

    def test_multiple_substitutions(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        result = g._render_template("app_build.gradle.kts", PACKAGE_NAME="com.example.app")
        assert result.count("com.example.app") == 2  # namespace and applicationId
        assert "{PACKAGE_NAME}" not in result

    def test_static_template_unchanged(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        result = g._render_template("colors.xml")
        assert "#6200EE" in result


# ---------------------------------------------------------------------------
# File generation (filesystem)
# ---------------------------------------------------------------------------


class TestCreateResourceFiles:
    def setup_method(self) -> None:
        pass

    def test_strings_xml_contains_app_name(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="Cool App")
        res_dir = tmp_path / "values"
        res_dir.mkdir(parents=True)
        g._create_resource_files(res_dir.parent)
        content = (res_dir / "strings.xml").read_text()
        assert "Cool App" in content

    def test_colors_xml_created(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        res_dir = tmp_path / "values"
        res_dir.mkdir(parents=True)
        g._create_resource_files(res_dir.parent)
        assert (res_dir / "colors.xml").exists()

    def test_themes_xml_created(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        res_dir = tmp_path / "values"
        res_dir.mkdir(parents=True)
        g._create_resource_files(res_dir.parent)
        assert (res_dir / "themes.xml").exists()


class TestCreateAndroidManifest:
    def test_app_name_in_manifest(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="My App")
        dest = tmp_path / "My_App" / "app" / "src" / "main"
        dest.mkdir(parents=True)
        g._create_android_manifest()
        content = (dest / "AndroidManifest.xml").read_text()
        assert 'android:label="My App"' in content

    def test_manifest_has_internet_permission(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path)
        dest = tmp_path / "My_App" / "app" / "src" / "main"
        dest.mkdir(parents=True)
        g._create_android_manifest()
        content = (dest / "AndroidManifest.xml").read_text()
        assert "android.permission.INTERNET" in content


class TestCreateMainActivity:
    def _java_dir(self, tmp_path: Path, package_name: str) -> Path:
        java_dir = (
            tmp_path / "My_App" / "app" / "src" / "main" / "java" / Path(*package_name.split("."))
        )
        java_dir.mkdir(parents=True)
        return java_dir

    def test_package_name_in_activity(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="My App", url="https://example.com")
        java_dir = self._java_dir(tmp_path, g.package_name)
        g._create_main_activity(java_dir)
        content = (java_dir / "MainActivity.kt").read_text()
        assert f"package {g.package_name}" in content

    def test_url_in_activity(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, url="https://mysite.com")
        java_dir = self._java_dir(tmp_path, g.package_name)
        g._create_main_activity(java_dir)
        content = (java_dir / "MainActivity.kt").read_text()
        assert "https://mysite.com" in content

    def test_no_leftover_placeholders(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="My App", url="https://example.com")
        java_dir = self._java_dir(tmp_path, g.package_name)
        g._create_main_activity(java_dir)
        content = (java_dir / "MainActivity.kt").read_text()
        assert "{PACKAGE_NAME}" not in content
        assert "{APP_URL}" not in content


class TestCreateGradleFiles:
    def test_package_name_in_app_build_gradle(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="My App")
        g.project_dir.mkdir(parents=True)
        (g.project_dir / "app").mkdir()
        (g.project_dir / "gradle" / "wrapper").mkdir(parents=True)
        g._create_gradle_files()
        content = (g.project_dir / "app" / "build.gradle.kts").read_text()
        assert g.package_name in content

    def test_app_name_in_settings_gradle(self, tmp_path: Path) -> None:
        g = make_gen(tmp_path, app_name="My App")
        g.project_dir.mkdir(parents=True)
        (g.project_dir / "app").mkdir()
        (g.project_dir / "gradle" / "wrapper").mkdir(parents=True)
        g._create_gradle_files()
        content = (g.project_dir / "settings.gradle.kts").read_text()
        assert "My App" in content
