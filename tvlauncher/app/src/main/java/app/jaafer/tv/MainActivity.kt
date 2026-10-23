package app.jaafer.tv

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
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
import kotlinx.coroutines.launch

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
    var screen by remember { mutableStateOf(Screen.Home) }
    var details by remember { mutableStateOf<AppEntry?>(null) }
    val isDefaultHome = remember {
        val home = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
        context.packageManager.resolveActivity(home, PackageManager.MATCH_DEFAULT_ONLY)?.activityInfo?.packageName == context.packageName
    }

    // Refresh on every return, so installed and removed apps show up without restarting.
    LifecycleResumeEffect(repo) {
        val job = scope.launch { apps = mergeApps(apps, repo.load()) }
        onPauseOrDispose { job.cancel() }
    }

    LaunchedEffect(homeSignal) {
        if (homeSignal > 0) {
            screen = Screen.Home
            details = null
        }
    }

    LaunchedEffect(apps) {
        val shown = details
        if (shown != null && apps?.none { it.pkg == shown.pkg } == true) details = null
    }

    val overlayOpen = screen != Screen.Home || details != null
    BackHandler(enabled = overlayOpen) {
        if (details != null) details = null else screen = Screen.Home
    }
    // As the TV's home screen there is nothing behind it, so Back stays here.
    BackHandler(enabled = !overlayOpen && isDefaultHome) { }

    Box(
        Modifier
            .fillMaxSize()
            .onPreviewKeyEvent { event ->
                if (event.key == Key.Menu && event.type == KeyEventType.KeyUp && !overlayOpen) {
                    screen = Screen.Control
                    true
                } else {
                    false
                }
            },
    ) {
        HomeScreen(
            apps = apps,
            gridState = gridState,
            overlayOpen = overlayOpen,
            resetSignal = homeSignal,
            onLaunch = { repo.launch(context, it) },
            onDetails = { details = it },
            onOpenControl = { screen = Screen.Control },
            onOpenSettings = { screen = Screen.Settings },
        )
        when (screen) {
            Screen.Control -> ControlCenter(onOpenSettings = { screen = Screen.Settings })
            Screen.Settings -> SettingsScreen()
            Screen.Home -> Unit
        }
        details?.let { app ->
            AppDetails(
                app = app,
                onOpen = {
                    details = null
                    repo.launch(context, app)
                },
                onPin = {
                    repo.pin(app.pkg)
                    apps = apps?.let { list -> listOf(app) + list.filter { it.pkg != app.pkg } }
                    details = null
                },
            )
        }
    }
}
