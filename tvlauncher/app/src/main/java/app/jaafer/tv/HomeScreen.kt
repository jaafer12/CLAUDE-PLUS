package app.jaafer.tv

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private const val COLUMNS = 5

@Composable
fun HomeScreen(
    apps: List<AppEntry>?,
    gridState: LazyGridState,
    overlayOpen: Boolean,
    resetSignal: Int,
    onLaunch: (AppEntry) -> Unit,
    onDetails: (AppEntry) -> Unit,
    onOpenControl: () -> Unit,
    onOpenSettings: () -> Unit,
) {
    var focused by remember { mutableStateOf<AppEntry?>(null) }
    var focusedRow by remember { mutableIntStateOf(0) }
    val firstTile = remember { FocusRequester() }
    val profileFocus = remember { FocusRequester() }
    val lastTarget = remember { arrayOfNulls<FocusRequester>(1) }
    val handledReset = remember { intArrayOf(0) }
    val now = rememberNow()

    val loaded = apps != null
    val empty = apps?.isEmpty() == true
    // Put focus back where it was after an overlay closes, or on the first app at start and on Home.
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

    Box(Modifier.fillMaxSize().background(Palette.Bg)) {
        Scene(Scenes.Sunset, Modifier.fillMaxWidth().fillMaxHeight(0.72f))
        Box(Modifier.fillMaxSize().graphicsLayer { alpha = dim }.background(Palette.Bg))

        Column(Modifier.fillMaxSize()) {
            TopBar(now, profileFocus, onOpenControl, onOpenSettings, onFocused = { focusedRow = 0 })

            AnimatedVisibility(
                visible = heroVisible,
                enter = fadeIn(tween(180)) + expandVertically(tween(200)),
                exit = fadeOut(tween(120)) + shrinkVertically(tween(200)),
            ) {
                Hero(focused, now)
            }

            when {
                apps == null -> Unit
                apps.isEmpty() -> Txt(
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
                    itemsIndexed(apps, key = { _, app -> app.pkg }) { index, app ->
                        val own = remember { FocusRequester() }
                        AppTile(
                            app = app,
                            modifier = Modifier
                                .focusRequester(own)
                                .then(if (index == 0) Modifier.focusRequester(firstTile) else Modifier),
                            onFocused = {
                                focused = app
                                focusedRow = index / COLUMNS
                                lastTarget[0] = own
                            },
                            onClick = { onLaunch(app) },
                            onLongClick = { onDetails(app) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TopBar(
    now: Long,
    profileFocus: FocusRequester,
    onOpenControl: () -> Unit,
    onOpenSettings: () -> Unit,
    onFocused: () -> Unit,
) {
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
        val context = LocalContext.current
        RoundIconButton(Icons.Search, "البحث", onFocused = onFocused) { Actions.search(context) }
        Spacer(Modifier.width(12.dp))
        RoundIconButton(Icons.Gear, "الإعدادات", onFocused = onFocused, onClick = onOpenSettings)
        Spacer(Modifier.width(18.dp))
        Txt(formatTime(now), 16.sp, weight = FontWeight.SemiBold)
    }
}

@Composable
private fun Hero(app: AppEntry?, now: Long) {
    Row(
        Modifier.fillMaxWidth().height(205.dp).padding(horizontal = 48.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(32.dp),
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Txt("${greeting(now)}، $USER_NAME", 14.sp, color = Palette.TextDim, weight = FontWeight.SemiBold)
            Txt(app?.label ?: "أهلاً بك", 48.sp, weight = FontWeight.Bold)
            Txt("اضغط «موافق» للفتح · اضغط مطوّلاً لمزيد من الخيارات", 13.sp, color = Palette.TextMuted)
        }
        if (app != null) {
            Image(
                bitmap = app.banner,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.width(290.dp).aspectRatio(16f / 9f).shadow(20.dp, TileShape).clip(TileShape),
            )
        }
    }
}

@Composable
private fun AppTile(
    app: AppEntry,
    modifier: Modifier,
    onFocused: () -> Unit,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    var focused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(if (focused) 1.12f else 1f, tween(140), label = "tile")
    Column(
        modifier
            .onFocusChanged {
                focused = it.isFocused
                if (it.isFocused) onFocused()
            }
            .tvClick(onLongClick, onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Image(
            bitmap = app.banner,
            contentDescription = app.label,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f)
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    shape = TileShape
                    clip = true
                    shadowElevation = if (focused) 18.dp.toPx() else 0f
                }
                .then(if (focused) Modifier.border(1.dp, Color(0x66FFFFFF), TileShape) else Modifier),
        )
        Txt(
            app.label,
            12.sp,
            Modifier.fillMaxWidth(),
            color = if (focused) Color.White else Color.Transparent,
            weight = FontWeight.SemiBold,
            align = TextAlign.Center,
        )
    }
}
