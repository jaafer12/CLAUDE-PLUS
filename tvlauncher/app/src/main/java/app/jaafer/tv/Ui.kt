package app.jaafer.tv

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.focusGroup
import androidx.compose.foundation.focusable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusProperties
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.addPathNodes
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

const val USER_NAME = "جعفر"

object Palette {
    val Bg = Color(0xFF0B0B0F)
    val Panel = Color(0xF22C2C34)
    val Glass = Color(0x2EFFFFFF)
    val GlassLow = Color(0x14FFFFFF)
    val TextDim = Color(0xD9FFFFFF)
    val TextMuted = Color(0x99FFFFFF)
    val Accent = Color(0xFFE9A066)
    val AccentInk = Color(0xFF1D1326)
    val SettingsBg = Color(0xFF1C1C1E)
}

val TileShape = RoundedCornerShape(14.dp)

@Composable
fun Txt(
    text: String,
    size: TextUnit,
    modifier: Modifier = Modifier,
    color: Color = Color.White,
    weight: FontWeight = FontWeight.Normal,
    maxLines: Int = 1,
    align: TextAlign = TextAlign.Start,
) {
    BasicText(
        text = text,
        modifier = modifier,
        style = TextStyle(color = color, fontSize = size, fontWeight = weight, textAlign = align),
        maxLines = maxLines,
        overflow = TextOverflow.Ellipsis,
    )
}

@Composable
fun Ico(icon: ImageVector, tint: Color, size: Dp) {
    Image(imageVector = icon, contentDescription = null, modifier = Modifier.size(size), colorFilter = ColorFilter.tint(tint))
}

@Composable
fun Avatar(size: Dp, ring: Boolean = false) {
    Box(
        Modifier
            .size(size)
            .clip(CircleShape)
            .background(Palette.Accent)
            .then(if (ring) Modifier.border(2.dp, Color.White, CircleShape) else Modifier),
        contentAlignment = Alignment.Center,
    ) {
        Txt(USER_NAME.take(1), (size.value * 0.45f).sp, color = Palette.AccentInk, weight = FontWeight.Bold)
    }
}

private fun isSelectKey(key: Key) = key == Key.DirectionCenter || key == Key.Enter || key == Key.NumPadEnter

/**
 * Remote-friendly click: fires on key up, and a held OK button fires [onLongClick] instead.
 * A key up whose key down went elsewhere (e.g. the press that opened this screen) is ignored.
 */
fun Modifier.tvClick(onLongClick: (() -> Unit)? = null, onClick: () -> Unit): Modifier = composed {
    val click = rememberUpdatedState(onClick)
    val longClick = rememberUpdatedState(onLongClick)
    val pressed = remember { intArrayOf(0) } // 0 idle, 1 down, 2 long press fired
    this
        .onKeyEvent { event ->
            if (!isSelectKey(event.key)) return@onKeyEvent false
            when (event.type) {
                KeyEventType.KeyDown -> {
                    val repeat = event.nativeKeyEvent.repeatCount
                    if (repeat == 0) {
                        pressed[0] = 1
                    } else if (pressed[0] == 1) {
                        longClick.value?.let { pressed[0] = 2; it() }
                    }
                }
                KeyEventType.KeyUp -> {
                    if (pressed[0] == 1) click.value()
                    pressed[0] = 0
                }
            }
            true
        }
        .pointerInput(Unit) {
            detectTapGestures(onLongPress = { longClick.value?.invoke() }, onTap = { click.value() })
        }
        .focusable()
}

/** Keeps D-pad focus inside an overlay so it never lands on the screen underneath. */
@OptIn(ExperimentalComposeUiApi::class)
fun Modifier.trapFocus(): Modifier = focusProperties { exit = { FocusRequester.Cancel } }.focusGroup()

/** Requests focus once the target is laid out; returns false if it never attached. */
suspend fun focusWhenReady(requester: FocusRequester): Boolean {
    repeat(10) {
        withFrameNanos { }
        if (runCatching { requester.requestFocus() }.isSuccess) return true
    }
    return false
}

/** A focusable row in the Apple TV style: white and lifted when focused, glass otherwise. */
@Composable
fun FocusRow(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(50),
    idle: Color = Palette.Glass,
    scaleTo: Float = 1.06f,
    contentPadding: PaddingValues = PaddingValues(horizontal = 18.dp),
    arrangement: Arrangement.Horizontal = Arrangement.spacedBy(8.dp),
    label: String? = null,
    onFocused: () -> Unit = {},
    content: @Composable RowScope.(focused: Boolean) -> Unit,
) {
    var focused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(if (focused) scaleTo else 1f, tween(120), label = "focus")
    Row(
        modifier
            .then(if (label != null) Modifier.semantics { contentDescription = label } else Modifier)
            .graphicsLayer { scaleX = scale; scaleY = scale }
            .shadow(if (focused) 14.dp else 0.dp, shape)
            .clip(shape)
            .background(if (focused) Color.White else idle)
            .onFocusChanged {
                focused = it.isFocused
                if (it.isFocused) onFocused()
            }
            .tvClick(onClick = onClick)
            .padding(contentPadding),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = arrangement,
    ) {
        content(focused)
    }
}

@Composable
fun PillButton(text: String, icon: ImageVector?, modifier: Modifier = Modifier, onClick: () -> Unit) {
    FocusRow(onClick, modifier, contentPadding = PaddingValues(horizontal = 18.dp, vertical = 9.dp)) { focused ->
        val fg = if (focused) Palette.Bg else Color.White
        if (icon != null) Ico(icon, fg, 13.dp)
        Txt(text, 14.sp, color = fg, weight = FontWeight.SemiBold)
    }
}

@Composable
fun RoundIconButton(icon: ImageVector, label: String, modifier: Modifier = Modifier, onFocused: () -> Unit = {}, onClick: () -> Unit) {
    FocusRow(
        onClick,
        modifier.size(36.dp),
        shape = CircleShape,
        contentPadding = PaddingValues(0.dp),
        arrangement = Arrangement.Center,
        label = label,
        onFocused = onFocused,
        scaleTo = 1.12f,
    ) { focused ->
        Ico(icon, if (focused) Palette.Bg else Color.White, 16.dp)
    }
}

@Composable
fun rememberNow(): Long {
    val now by produceState(System.currentTimeMillis()) {
        while (true) {
            val t = System.currentTimeMillis()
            value = t
            delay(60_000 - t % 60_000)
        }
    }
    return now
}

private val arabic: Locale = Locale.forLanguageTag("ar")

fun formatTime(t: Long): String = SimpleDateFormat("h:mm", arabic).format(Date(t))

fun formatDate(t: Long): String = SimpleDateFormat("EEEE، d MMMM", arabic).format(Date(t))

fun greeting(t: Long): String {
    val hour = Calendar.getInstance().apply { timeInMillis = t }.get(Calendar.HOUR_OF_DAY)
    return if (hour in 4..11) "صباح الخير" else "مساء الخير"
}

private fun circle(cx: Float, cy: Float, r: Float) = "M${cx - r},${cy}a$r,$r 0 1,0 ${2 * r},0a$r,$r 0 1,0 ${-2 * r},0"

private fun stroke(vararg paths: String): ImageVector {
    val builder = ImageVector.Builder(defaultWidth = 24.dp, defaultHeight = 24.dp, viewportWidth = 24f, viewportHeight = 24f)
    for (d in paths) {
        builder.addPath(
            pathData = addPathNodes(d),
            stroke = SolidColor(Color.White),
            strokeLineWidth = 2f,
            strokeLineCap = StrokeCap.Round,
            strokeLineJoin = StrokeJoin.Round,
        )
    }
    return builder.build()
}

private fun fill(d: String): ImageVector =
    ImageVector.Builder(defaultWidth = 24.dp, defaultHeight = 24.dp, viewportWidth = 24f, viewportHeight = 24f)
        .addPath(pathData = addPathNodes(d), fill = SolidColor(Color.White))
        .build()

/** Line icons drawn from the design, so no icon library is bundled. */
object Icons {
    val Play = fill("M6 4l14 8-14 8z")
    val Plus = stroke("M12 5v14M5 12h14")
    val Minus = stroke("M5 12h14")
    val Search = stroke(circle(11f, 11f, 7f), "M20 20l-4-4")
    val Wifi = stroke("M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0", circle(12f, 19.5f, 0.6f))
    val Power = stroke("M12 3v9", "M6.3 7.3a8 8 0 1 0 11.4 0")
    val Volume = stroke("M11 5L6 9H3v6h3l5 4z", "M15.5 8.5a5 5 0 0 1 0 7")
    val Chevron = stroke("M15 5l-7 7 7 7")
    val Info = stroke(circle(12f, 12f, 9f), "M12 11v5", "M12 8h0.01")
    val Globe = stroke(circle(12f, 12f, 9f), "M3 12h18", "M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18")
    val Clock = stroke(circle(12f, 12f, 9f), "M12 7v5l3 2")
    val Apps = stroke("M4 4h6v6H4z", "M14 4h6v6h-6z", "M4 14h6v6H4z", "M14 14h6v6h-6z")
    val Remote = stroke("M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z", circle(12f, 8f, 2f), "M10 14h0.01M14 14h0.01M10 17h0.01M14 17h0.01")
    val Person = stroke(circle(12f, 8f, 4f), "M4 21a8 8 0 0 1 16 0")
    val Tv = stroke("M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z", "M8 21h8M12 17v4")
    val Home = stroke("M3 11l9-8 9 8", "M5 10v10h14V10")
    val Trash = stroke("M4 7h16", "M9 7V4h6v3", "M6 7l1 13h10l1-13")
    val ToFront = stroke("M12 19V5", "M5 12l7-7 7 7")
    val Sun = stroke(circle(12f, 12f, 4f), "M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4")
    val Moon = stroke("M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z")
    val Cloud = stroke("M7 18h10a4 4 0 0 0 0-8a6 6 0 0 0-11.5 1.5A3.5 3.5 0 0 0 7 18z")
    val CloudSun = stroke("M8 3v1M3 8h1M4.5 4.5l0.7 0.7M11.5 4.5l-0.7 0.7", "M5.5 10.5a3 3 0 0 1 5.5-3", "M7 18h10a4 4 0 0 0 0-8a6 6 0 0 0-11.5 1.5A3.5 3.5 0 0 0 7 18z")
    val Rain = stroke("M7 15h10a4 4 0 0 0 0-8a6 6 0 0 0-11.5 1.5A3.5 3.5 0 0 0 7 15z", "M8 18l-1 3M12 18l-1 3M16 18l-1 3")
    val Snow = stroke("M7 15h10a4 4 0 0 0 0-8a6 6 0 0 0-11.5 1.5A3.5 3.5 0 0 0 7 15z", "M8 19h0.01M12 21h0.01M16 19h0.01M10 22h0.01M14 22h0.01")
    val Storm = stroke("M7 15h10a4 4 0 0 0 0-8a6 6 0 0 0-11.5 1.5A3.5 3.5 0 0 0 7 15z", "M13 15l-3 4h4l-3 4")
    val Gear = stroke(
        circle(12f, 12f, 3f),
        "M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
    )
}
