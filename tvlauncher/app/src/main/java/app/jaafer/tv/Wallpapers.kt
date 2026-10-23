package app.jaafer.tv

import android.content.Context
import android.graphics.BitmapFactory
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.util.Calendar

class Wallpaper(val image: ImageBitmap, val credit: String)

/** Photos bundled under assets/wallpapers/{day,night} by tools/fetch_wallpapers.py at build time. */
object Wallpapers {
    private var sets: Map<String, List<String>>? = null
    private var credits: Map<String, String> = emptyMap()

    @Synchronized
    private fun sets(context: Context): Map<String, List<String>> {
        sets?.let { return it }
        val assets = context.assets
        val found = listOf("day", "night").associateWith { part ->
            (runCatching { assets.list("wallpapers/$part") }.getOrNull() ?: emptyArray())
                .filter { it.endsWith(".webp") }
                .sorted()
                .map { "$part/$it" }
        }
        credits = runCatching {
            val o = JSONObject(assets.open("wallpapers/credits.json").bufferedReader().use { it.readText() })
            o.keys().asSequence().associateWith { o.getString(it) }
        }.getOrDefault(emptyMap())
        sets = found
        return found
    }

    fun isNight(): Boolean {
        val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        return hour < 6 || hour >= 18
    }

    /** The set for this time of day, or every photo if that set is empty. */
    fun paths(context: Context): List<String> {
        val all = sets(context)
        return all[if (isNight()) "night" else "day"].orEmpty().ifEmpty { all.values.flatten() }
    }

    fun load(context: Context, path: String): Wallpaper? = runCatching {
        val bitmap = context.assets.open("wallpapers/$path").use { BitmapFactory.decodeStream(it) }
        bitmap.prepareToDraw()
        Wallpaper(bitmap.asImageBitmap(), credits[path].orEmpty())
    }.getOrNull()
}

/** Cycles through the photos for the time of day; null when none are bundled. */
@Composable
fun rememberWallpaper(intervalMs: Long): Wallpaper? {
    val context = LocalContext.current
    val wallpaper by produceState<Wallpaper?>(null, intervalMs) {
        var i = (0..999).random()
        while (true) {
            val next = withContext(Dispatchers.IO) {
                val paths = Wallpapers.paths(context)
                if (paths.isEmpty()) null else Wallpapers.load(context, paths[i++ % paths.size])
            }
            if (next == null && value == null) return@produceState
            if (next != null) value = next
            delay(intervalMs)
        }
    }
    return wallpaper
}

/** The home screen background: a photo that changes slowly, or the drawn landscape without photos. */
@Composable
fun Backdrop(wallpaper: Wallpaper?, modifier: Modifier = Modifier) {
    Box(modifier) {
        if (wallpaper == null) {
            Scene(Scenes.Sunset, Modifier.fillMaxWidth().fillMaxHeight(0.72f))
        } else {
            Photo(wallpaper)
        }
    }
}

@Composable
private fun Photo(wallpaper: Wallpaper) {
    Box(Modifier.fillMaxSize()) {
        Crossfade(wallpaper, animationSpec = tween(1500), label = "wallpaper") { w ->
            Image(bitmap = w.image, contentDescription = null, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        }
        // Keeps text readable: darker at the top bar, both sides and behind the app rows.
        Spacer(
            Modifier.fillMaxSize().drawWithCache {
                val down = Brush.verticalGradient(
                    0f to Color(0x80000000),
                    0.18f to Color.Transparent,
                    0.42f to Color(0x260B0B0F),
                    0.62f to Palette.Bg.copy(alpha = 0.9f),
                    1f to Palette.Bg,
                )
                val sides = Brush.horizontalGradient(
                    0f to Color(0x8C000000),
                    0.35f to Color.Transparent,
                    0.6f to Color.Transparent,
                    1f to Color(0x99000000),
                )
                onDrawBehind {
                    drawRect(sides)
                    drawRect(down)
                }
            },
        )
    }
}

/** Full-screen photos drifting slowly, with the clock and weather; used in the app and as the system screensaver. */
@Composable
fun Screensaver(modifier: Modifier = Modifier) {
    val wallpaper = rememberWallpaper(20_000)
    val now = rememberNow()
    val weather = rememberWeather()
    val drift = rememberInfiniteTransition(label = "drift")
    val scale by drift.animateFloat(
        initialValue = 1f,
        targetValue = 1.08f,
        animationSpec = infiniteRepeatable(tween(20_000, easing = LinearEasing), RepeatMode.Reverse),
        label = "scale",
    )
    Box(modifier.fillMaxSize().background(Color.Black)) {
        if (wallpaper == null) {
            Scene(Scenes.Sunset, Modifier.fillMaxSize())
        } else {
            Crossfade(wallpaper, animationSpec = tween(2000), label = "screensaver") { w ->
                Image(
                    bitmap = w.image,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize().graphicsLayer {
                        scaleX = scale
                        scaleY = scale
                    },
                )
            }
        }
        Spacer(Modifier.fillMaxSize().background(Brush.verticalGradient(0.5f to Color.Transparent, 1f to Color(0xB3000000))))
        Row(
            Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(horizontal = 48.dp, vertical = 36.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            Txt(
                wallpaper?.credit?.takeIf { it.isNotEmpty() }?.let { "الصورة: $it" }.orEmpty(),
                11.sp,
                Modifier.weight(1f),
                color = Palette.TextMuted,
            )
            ClockWeather(now, weather)
        }
    }
}
