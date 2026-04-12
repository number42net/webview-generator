package {PACKAGE_NAME}

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

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private val FILE_CHOOSER_REQUEST_CODE = 1

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Create layout programmatically
        val container = FrameLayout(this)
        webView = WebView(this)

        webView.isFocusable = true
        webView.isFocusableInTouchMode = true
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            webView.isForceDarkAllowed = false
        }

        container.addView(webView, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        ))
        setContentView(container)

        // Remove "wv" from user agent to prevent WebView detection
        val defaultUA = webView.settings.userAgentString
        webView.settings.userAgentString = defaultUA.replace("; wv", "")

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val url = request?.url.toString()

                // Handle external links
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    return false // Load in WebView
                }

                // Handle other schemes (tel:, mailto:, etc.)
                try {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    return true
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "Cannot open link", Toast.LENGTH_SHORT).show()
                    return true
                }
            }

            override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
                super.onPageStarted(view, url, favicon)
                // Inject visibilitychange blocking as early as possible
                view?.evaluateJavascript("document.addEventListener(\"visibilitychange\",function (event) {event.stopImmediatePropagation();},true);", null)
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                // Page finished loading

                // Stop visibilitychange event propagation
                view?.evaluateJavascript("document.addEventListener(\"visibilitychange\",function (event) {event.stopImmediatePropagation();},true);", null)

                // FIX: dvh (dynamic viewport height) CSS unit resolves to 0 in some WebView configs.
                // Inject CSS to make dvh fall back to vh for any element using it.
                view?.evaluateJavascript("""
                    (function() {
                        if (!document.getElementById('dvh-fix')) {
                            var style = document.createElement('style');
                            style.id = 'dvh-fix';
                            style.textContent = '*, *::before, *::after { --dvh-fix: 1vh; } [class*="h-dvh"] { height: 100vh !important; } [class*="min-h-dvh"] { min-height: 100vh !important; } [class*="max-h-dvh"] { max-height: 100vh !important; }';
                            document.head.appendChild(style);
                        }
                    })()
                """.trimIndent(), null)

            }

            override fun onLoadResource(view: WebView?, url: String?) {
                super.onLoadResource(view, url)
                // Also inject visibilitychange blocking in onLoadResource
                view?.evaluateJavascript("document.addEventListener(\"visibilitychange\", (event) => { event.stopImmediatePropagation(); }, true);", null)
            }

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                super.onReceivedError(view, request, error)
                // Only show error for main frame failures
                if (request?.isForMainFrame == true) {
                    Toast.makeText(
                        this@MainActivity,
                        "Page load error: ${error?.description ?: "Unknown error"}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }

        // Set WebChromeClient for file upload support and loading progress
        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                super.onProgressChanged(view, newProgress)
                // Show loading progress
                // Progress: newProgress
            }

            override fun onShowCustomView(view: android.view.View?, callback: CustomViewCallback?) {
                super.onShowCustomView(view, callback)
            }

            override fun onCreateWindow(view: WebView?, isDialog: Boolean, isUserGesture: Boolean, resultMsg: android.os.Message?): Boolean {
                return false
            }

            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                this@MainActivity.filePathCallback?.onReceiveValue(null)
                this@MainActivity.filePathCallback = filePathCallback

                val intent = fileChooserParams?.createIntent()
                if (intent == null) {
                    this@MainActivity.filePathCallback = null
                    Toast.makeText(this@MainActivity, "Cannot open file chooser", Toast.LENGTH_SHORT).show()
                    return false
                }

                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST_CODE)
                } catch (e: Exception) {
                    this@MainActivity.filePathCallback = null
                    Toast.makeText(this@MainActivity, "Cannot open file chooser", Toast.LENGTH_SHORT).show()
                    return false
                }
                return true
            }
        }

        // Configure WebView settings
        webView.settings.apply {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                safeBrowsingEnabled = false
            }
            setDomStorageEnabled(true)
            databaseEnabled = true
            setAllowFileAccess(true)
            setBlockNetworkLoads(false)
            javaScriptEnabled = true
        }

        // Disable X-Requested-With header to prevent WebView detection
        try {
            if (WebViewFeature.isFeatureSupported(WebViewFeature.REQUESTED_WITH_HEADER_ALLOW_LIST)) {
                WebSettingsCompat.setRequestedWithHeaderOriginAllowList(
                    webView.settings,
                    emptySet()
                )
            }
        } catch (_: Exception) {}

        // Enable persistent cookies and storage
        android.webkit.CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, true)
        }

        // Custom headers to prevent WebView detection
        val customHeaders = mapOf(
            "X-Requested-With" to "",
            "DNT" to "1"
        )

        webView.loadUrl("{APP_URL}", customHeaders)
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
        webView.resumeTimers()
    }

    override fun onPause() {
        webView.evaluateJavascript("document.querySelectorAll('audio').forEach(x => x.pause());document.querySelectorAll('video').forEach(x => x.pause());", null)
        android.webkit.CookieManager.getInstance().flush()
        webView.onPause()
        webView.pauseTimers()
        super.onPause()
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            val results = if (resultCode == Activity.RESULT_OK && data != null) {
                arrayOf(Uri.parse(data.dataString))
            } else {
                null
            }
            filePathCallback?.onReceiveValue(results)
            filePathCallback = null
        }
    }
}
