package app.jaafer.tv

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** An open folder: its apps over the dimmed home screen. Back closes it. */
@Composable
fun FolderView(name: String, apps: List<AppEntry>, active: Boolean, onLaunch: (AppEntry) -> Unit, onDetails: (AppEntry) -> Unit) {
    val first = remember { FocusRequester() }
    val lastDirection = remember { intArrayOf(0) }
    // Also re-runs when an app's details close, so focus comes back into the folder.
    LaunchedEffect(active) { if (active) focusWhenReady(first) }

    Box(
        Modifier
            .fillMaxSize()
            .background(Color(0xE60B0B0F))
            .trapFocus()
            .onPreviewKeyEvent {
                val direction = directionOf(it)
                if (direction != 0) lastDirection[0] = direction
                false
            },
    ) {
        Column(Modifier.fillMaxSize().padding(top = 48.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Txt(name, 28.sp, Modifier.fillMaxWidth(), weight = FontWeight.Bold, align = TextAlign.Center)
            LazyVerticalGrid(
                columns = GridCells.Fixed(COLUMNS),
                contentPadding = PaddingValues(start = 48.dp, end = 48.dp, top = 28.dp, bottom = 60.dp),
                horizontalArrangement = Arrangement.spacedBy(20.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxSize(),
            ) {
                itemsIndexed(apps, key = { _, app -> app.pkg }) { index, app ->
                    AppTile(
                        app,
                        lastDirection,
                        if (index == 0) Modifier.focusRequester(first) else Modifier,
                        onFocused = {},
                        onClick = { onLaunch(app) },
                        onLongClick = { onDetails(app) },
                    )
                }
            }
        }
    }
}
