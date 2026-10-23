package app.jaafer.tv

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEvent
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch

/** D-pad direction of a key event: 1 left, 2 right, 3 up, 4 down, 0 anything else. */
fun directionOf(event: KeyEvent): Int {
    if (event.type != KeyEventType.KeyDown) return 0
    return when (event.key) {
        Key.DirectionLeft -> 1
        Key.DirectionRight -> 2
        Key.DirectionUp -> 3
        Key.DirectionDown -> 4
        else -> 0
    }
}

private val TiltSpring = spring<Float>(dampingRatio = 0.42f, stiffness = 260f)

/**
 * An Apple TV style card: lifts and casts a shadow when focused, and tilts toward each
 * D-pad press before springing back. [lastDirection] is the press that moved focus here,
 * so the newly focused card swings in from that side.
 */
@Composable
fun FocusTile(
    label: String,
    lastDirection: IntArray,
    modifier: Modifier = Modifier,
    onFocused: () -> Unit,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
    content: @Composable BoxScope.() -> Unit,
) {
    var focused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(if (focused) 1.12f else 1f, tween(140), label = "tile")
    val tiltX = remember { Animatable(0f) }
    val tiltY = remember { Animatable(0f) }
    val scope = rememberCoroutineScope()

    fun tilt(direction: Int) {
        val (x, y) = when (direction) {
            1 -> 0f to -9f
            2 -> 0f to 9f
            3 -> 7f to 0f
            4 -> -7f to 0f
            else -> return
        }
        scope.launch { tiltX.snapTo(x); tiltX.animateTo(0f, TiltSpring) }
        scope.launch { tiltY.snapTo(y); tiltY.animateTo(0f, TiltSpring) }
    }

    Column(
        modifier
            .onPreviewKeyEvent {
                if (focused) tilt(directionOf(it))
                false
            }
            .onFocusChanged {
                focused = it.isFocused
                if (it.isFocused) {
                    tilt(lastDirection[0])
                    onFocused()
                }
            }
            .tvClick(onLongClick, onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Box(
            Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f)
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    rotationX = tiltX.value
                    rotationY = tiltY.value
                    cameraDistance = 14f * density
                    shape = TileShape
                    clip = true
                    shadowElevation = if (focused) 18.dp.toPx() else 0f
                }
                .then(if (focused) Modifier.border(1.dp, Color(0x66FFFFFF), TileShape) else Modifier),
            content = content,
        )
        Txt(
            label,
            12.sp,
            Modifier.fillMaxWidth(),
            color = if (focused) Color.White else Color.Transparent,
            weight = FontWeight.SemiBold,
            align = TextAlign.Center,
        )
    }
}

@Composable
fun AppTile(app: AppEntry, lastDirection: IntArray, modifier: Modifier, onFocused: () -> Unit, onClick: () -> Unit, onLongClick: () -> Unit) {
    FocusTile(app.label, lastDirection, modifier, onFocused, onClick, onLongClick) {
        Image(bitmap = app.banner, contentDescription = app.label, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
    }
}

private val MiniShape = RoundedCornerShape(6.dp)

/** A folder shows up to four of its apps in a 2×2 grid on frosted glass. */
@Composable
fun FolderTile(folder: FolderItem, lastDirection: IntArray, modifier: Modifier, onFocused: () -> Unit, onClick: () -> Unit) {
    FocusTile(folder.name, lastDirection, modifier, onFocused, onClick, onLongClick = onClick) {
        Column(
            Modifier.fillMaxSize().background(Color(0x40FFFFFF)).padding(7.dp),
            verticalArrangement = Arrangement.spacedBy(5.dp),
        ) {
            for (row in 0 until 2) {
                Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    for (col in 0 until 2) {
                        val app = folder.apps.getOrNull(row * 2 + col)
                        val cell = Modifier.weight(1f).fillMaxSize().clip(MiniShape)
                        if (app != null) {
                            Image(bitmap = app.banner, contentDescription = null, contentScale = ContentScale.Crop, modifier = cell)
                        } else {
                            Spacer(cell.background(Color(0x1AFFFFFF)))
                        }
                    }
                }
            }
        }
    }
}
