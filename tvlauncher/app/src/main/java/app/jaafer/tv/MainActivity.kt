package app.jaafer.tv

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.SystemClock
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.lifecycle.compose.LifecycleResumeEffect
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private const val IDLE_MS = 5 * 60 * 1000L

class MainActivity : ComponentActivity() {
    private val homeSignal = mutableIntStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val repo = AppRepository(this)
        setContent {
            CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
                LauncherApp(repo, homeSignal.intValue)
            }
        }
    }

    // Pressing Home while the launcher is already showing returns to the top of the home screen.
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        if (intent.hasCategory(Intent.CATEGORY_HOME)) homeSignal.intValue++
    }
}

private enum class Screen { Home, Control, Settings }

@Composable
private fun LauncherApp(repo: AppRepository, homeSignal: Int) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val gridState = rememberLazyGridState()
    var apps by remember { mutableStateOf<List<AppEntry>?>(null) }
    var folders by remember { mutableStateOf(repo.folders()) }
    var screen by remember { mutableStateOf(Screen.Home) }
    var details by remember { mutableStateOf<AppEntry?>(null) }
    var openFolder by remember { mutableStateOf<String?>(null) }
    var forecast by remember { mutableStateOf<Weather?>(null) }
    var screensaver by remember { mutableStateOf(false) }
    val lastInput = remember { longArrayOf(SystemClock.uptimeMillis()) }
    val isDefaultHome = remember {
        val home = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        context.packageManager.resolveActivity(home, PackageManager.MATCH_DEFAULT_ONLY)?.activityInfo?.packageName == context.packageName
    }

    // Refresh apps on every return, and start the screensaver after a few idle minutes.
    LifecycleResumeEffect(repo) {
        lastInput[0] = SystemClock.uptimeMillis()
        val refresh = scope.launch { apps = mergeApps(apps, repo.load()) }
        val idle = scope.launch {
            while (true) {
                delay(15_000)
                if (SystemClock.uptimeMillis() - lastInput[0] > IDLE_MS) screensaver = true
            }
        }
        onPauseOrDispose {
            refresh.cancel()
            idle.cancel()
            screensaver = false
        }
    }

    LaunchedEffect(homeSignal) {
        if (homeSignal > 0) {
            screen = Screen.Home
            details = null
            openFolder = null
            forecast = null
        }
    }

    val items = remember(apps, folders) { apps?.let { buildHomeItems(it, folders) } }
    val folderApps = openFolder?.let { name -> apps?.filter { folders[it.pkg] == name } }.orEmpty()

    LaunchedEffect(apps) {
        val shown = details
        if (shown != null && apps?.none { it.pkg == shown.pkg } == true) details = null
    }
    LaunchedEffect(folderApps.isEmpty()) {
        if (openFolder != null && folderApps.isEmpty() && apps != null) openFolder = null
    }

    val overlayOpen = screen != Screen.Home || details != null || openFolder != null || forecast != null
    BackHandler(enabled = overlayOpen) {
        when {
            details != null -> details = null
            forecast != null -> forecast = null
            openFolder != null -> openFolder = null
            else -> screen = Screen.Home
        }
    }
    // As the TV's home screen there is nothing behind it, so Back stays here.
    BackHandler(enabled = !overlayOpen && isDefaultHome) { }

    Box(
        Modifier
            .fillMaxSize()
            .onPreviewKeyEvent { event ->
                lastInput[0] = SystemClock.uptimeMillis()
                when {
                    // Any key wakes the screensaver and is not passed on.
                    screensaver -> {
                        if (event.type == KeyEventType.KeyUp) screensaver = false
                        true
                    }
                    event.key == Key.Menu && event.type == KeyEventType.KeyUp && !overlayOpen -> {
                        screen = Screen.Control
                        true
                    }
                    else -> false
                }
            },
    ) {
        HomeScreen(
            items = items,
            gridState = gridState,
            overlayOpen = overlayOpen,
            resetSignal = homeSignal,
            onLaunch = { repo.launch(context, it) },
            onDetails = { details = it },
            onOpenFolder = { openFolder = it },
            onOpenControl = { screen = Screen.Control },
            onOpenSettings = { screen = Screen.Settings },
            onOpenForecast = { forecast = it },
        )
        openFolder?.let { name ->
            FolderView(
                name,
                folderApps,
                active = details == null,
                onLaunch = { repo.launch(context, it) },
                onDetails = { details = it },
            )
        }
        forecast?.let { ForecastPanel(it, onClose = { forecast = null }) }
        when (screen) {
            Screen.Control -> ControlCenter(
                onOpenSettings = { screen = Screen.Settings },
                onScreensaver = {
                    screen = Screen.Home
                    screensaver = true
                },
            )
            Screen.Settings -> SettingsScreen()
            Screen.Home -> Unit
        }
        details?.let { app ->
            AppDetails(
                app = app,
                folder = folders[app.pkg],
                onOpen = {
                    details = null
                    repo.launch(context, app)
                },
                onPin = {
                    repo.pin(app.pkg)
                    apps = apps?.let { list -> listOf(app) + list.filter { it.pkg != app.pkg } }
                    details = null
                },
                onSetFolder = { name ->
                    repo.setFolder(app.pkg, name)
                    folders = repo.folders()
                    details = null
                },
            )
        }
        if (screensaver) Screensaver()
    }
}
