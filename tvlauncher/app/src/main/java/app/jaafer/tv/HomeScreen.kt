package app.jaafer.tv

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyGridState
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.NumberFormat
import java.util.Locale

const val COLUMNS = 5

private val arabicCount: NumberFormat = NumberFormat.getIntegerInstance(Locale.forLanguageTag("ar"))

@Composable
fun HomeScreen(
    items: List<HomeItem>?,
    gridState: LazyGridState,
    overlayOpen: Boolean,
    resetSignal: Int,
    onLaunch: (AppEntry) -> Unit,
    onDetails: (AppEntry) -> Unit,
    onOpenFolder: (String) -> Unit,
    onOpenControl: () -> Unit,
    onOpenSettings: () -> Unit,
    onOpenForecast: (Weather) -> Unit,
) {
    var focused by remember { mutableStateOf<HomeItem?>(null) }
    var focusedRow by remember { mutableIntStateOf(0) }
    val firstTile = remember { FocusRequester() }
    val profileFocus = remember { FocusRequester() }
    val lastTarget = remember { arrayOfNulls<FocusRequester>(1) }
    val handledReset = remember { intArrayOf(0) }
    val lastDirection = remember { intArrayOf(0) }
    val now = rememberNow()
    val weather = rememberWeather()
    val wallpaper = rememberWallpaper(90_000)

    val loaded = items != null
    val empty = items?.isEmpty() == true
    // Put focus back where it was after an overlay closes, or on the first item at start and on Home.
    LaunchedEffect(overlayOpen, loaded, resetSignal) {
        if (overlayOpen || !loaded) return@LaunchedEffect
        if (resetSignal != handledReset[0]) {
            handledReset[0] = resetSignal
            lastTarget[0] = null
            if (!empty) gridState.scrollToItem(0)
        }
        val target = lastTarget[0]
        if (target != null && focusWhenReady(target)) return@LaunchedEffect
        focusWhenReady(if (empty) profileFocus else firstTile)
    }

    val heroVisible = focusedRow == 0
    val dim by animateFloatAsState(if (heroVisible) 0f else 0.7f, tween(220), label = "dim")

    Box(
        Modifier
            .fillMaxSize()
            .background(Palette.Bg)
            .onPreviewKeyEvent {
                val direction = directionOf(it)
                if (direction != 0) lastDirection[0] = direction
                false
            },
    ) {
        Backdrop(wallpaper, Modifier.fillMaxSize())
        Box(Modifier.fillMaxSize().graphicsLayer { alpha = dim }.background(Palette.Bg))

        Column(Modifier.fillMaxSize()) {
            TopBar(now, showClock = !heroVisible, profileFocus, onOpenControl, onOpenSettings, onFocused = { focusedRow = 0 })

            AnimatedVisibility(
                visible = heroVisible,
                enter = fadeIn(tween(180)) + expandVertically(tween(200)),
                exit = fadeOut(tween(120)) + shrinkVertically(tween(200)),
            ) {
                Hero(focused, now, weather, wallpaper?.credit, onWeatherFocused = { focusedRow = 0 }, onOpenForecast)
            }

            when {
                items == null -> Unit
                items.isEmpty() -> Txt(
                    "لا توجد تطبيقات مثبّتة",
                    16.sp,
                    Modifier.fillMaxWidth().padding(top = 40.dp),
                    color = Palette.TextMuted,
                    align = TextAlign.Center,
                )
                else -> LazyVerticalGrid(
                    columns = GridCells.Fixed(COLUMNS),
                    state = gridState,
                    contentPadding = PaddingValues(start = 48.dp, end = 48.dp, top = 20.dp, bottom = 60.dp),
                    horizontalArrangement = Arrangement.spacedBy(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    itemsIndexed(items, key = { _, item -> item.key }) { index, item ->
                        val own = remember { FocusRequester() }
                        val modifier = Modifier
                            .focusRequester(own)
                            .then(if (index == 0) Modifier.focusRequester(firstTile) else Modifier)
                        val onFocused = {
                            focused = item
                            focusedRow = index / COLUMNS
                            lastTarget[0] = own
                        }
                        when (item) {
                            is AppItem -> AppTile(
                                item.app,
                                lastDirection,
                                modifier,
                                onFocused,
                                onClick = { onLaunch(item.app) },
                                onLongClick = { onDetails(item.app) },
                            )
                            is FolderItem -> FolderTile(item, lastDirection, modifier, onFocused) { onOpenFolder(item.name) }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TopBar(
    now: Long,
    showClock: Boolean,
    profileFocus: FocusRequester,
    onOpenControl: () -> Unit,
    onOpenSettings: () -> Unit,
    onFocused: () -> Unit,
) {
    val context = LocalContext.current
    Row(
        Modifier.fillMaxWidth().padding(start = 40.dp, end = 48.dp, top = 22.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        FocusRow(
            onClick = onOpenControl,
            modifier = Modifier.focusRequester(profileFocus),
            idle = Color.Transparent,
            contentPadding = PaddingValues(start = 6.dp, end = 14.dp, top = 5.dp, bottom = 5.dp),
            arrangement = Arrangement.spacedBy(10.dp),
            label = "مركز التحكم",
            onFocused = onFocused,
        ) { focused ->
            Avatar(28.dp)
            Txt(USER_NAME, 13.sp, color = if (focused) Palette.Bg else Palette.TextDim, weight = FontWeight.SemiBold)
        }
        Spacer(Modifier.weight(1f))
        FocusRow(
            onClick = { Actions.voiceSearch(context) },
            modifier = Modifier.height(36.dp),
            contentPadding = PaddingValues(horizontal = 16.dp),
            onFocused = onFocused,
        ) { focused ->
            val fg = if (focused) Palette.Bg else Color.White
            Ico(Icons.Mic, fg, 16.dp)
            Txt("بحث صوتي", 13.sp, color = fg, weight = FontWeight.SemiBold)
        }
        Spacer(Modifier.width(12.dp))
        RoundIconButton(Icons.Gear, "الإعدادات", onFocused = onFocused, onClick = onOpenSettings)
        if (showClock) {
            Spacer(Modifier.width(18.dp))
            Txt(formatTime(now), 16.sp, weight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun Hero(
    item: HomeItem?,
    now: Long,
    weather: Weather?,
    credit: String?,
    onWeatherFocused: () -> Unit,
    onOpenForecast: (Weather) -> Unit,
) {
    val (title, hint) = when (item) {
        is AppItem -> item.app.label to "اضغط «موافق» للفتح · اضغط مطوّلاً لمزيد من الخيارات"
        is FolderItem -> item.name to "مجلد · ${arabicCount.format(item.apps.size.toLong())} تطبيقات"
        null -> "أهلاً بك" to ""
    }
    Row(
        Modifier.fillMaxWidth().height(232.dp).padding(start = 48.dp, end = 48.dp, top = 18.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(32.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Txt("${greeting(now)}، $USER_NAME", 14.sp, color = Palette.TextDim, weight = FontWeight.SemiBold)
            Txt(title, 48.sp, weight = FontWeight.Bold)
            Txt(hint, 13.sp, color = Palette.TextMuted)
        }
        Column(horizontalAlignment = Alignment.End) {
            ClockWeather(
                now,
                weather,
                onWeatherFocused = onWeatherFocused,
                onWeatherClick = weather?.let { w -> { onOpenForecast(w) } },
            )
            if (!credit.isNullOrEmpty()) Txt("الصورة: $credit", 9.sp, Modifier.padding(top = 4.dp, end = 12.dp), color = Color(0x80FFFFFF))
        }
    }
}
