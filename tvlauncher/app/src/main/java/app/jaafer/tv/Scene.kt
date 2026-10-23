package app.jaafer.tv

import androidx.compose.foundation.layout.Spacer
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithCache
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path

class SceneColors(val sky: List<Color>, val sun: Color, val back: Color, val front: Color, val fade: Color)

object Scenes {
    val Sunset = SceneColors(
        sky = listOf(Color(0xFF16234A), Color(0xFF4B2F63), Color(0xFFC46A52), Color(0xFFE9A066)),
        sun = Color(0xE6FFD9A0),
        back = Color(0xFF3A2244),
        front = Color(0xFF1D1326),
        fade = Palette.Bg,
    )
    val Sea = SceneColors(
        sky = listOf(Color(0xFF0F3B4A), Color(0xFF1B6A74), Color(0xFF0B2A33)),
        sun = Color(0xD9E8F4F0),
        back = Color(0xFF0A3440),
        front = Color(0xFF06222B),
        fade = Color(0xFF071318),
    )
}

/** The landscape behind the home and details screens; paths and brushes are built once per size. */
@Composable
fun Scene(colors: SceneColors, modifier: Modifier = Modifier) {
    Spacer(
        modifier.drawWithCache {
            val w = size.width
            val h = size.height

            fun ridge(top: Float, points: FloatArray) = Path().apply {
                val band = h - top
                moveTo(0f, h)
                var i = 0
                while (i < points.size) {
                    lineTo(w * points[i], top + band * points[i + 1])
                    i += 2
                }
                lineTo(w, h)
                close()
            }

            val back = ridge(h * 0.5f, floatArrayOf(0f, 0.6f, 0.14f, 0.2f, 0.26f, 0.52f, 0.4f, 0.08f, 0.55f, 0.48f, 0.7f, 0.18f, 0.84f, 0.5f, 1f, 0.26f))
            val front = ridge(h * 0.66f, floatArrayOf(0f, 0.5f, 0.18f, 0.24f, 0.34f, 0.6f, 0.5f, 0.3f, 0.66f, 0.64f, 0.82f, 0.34f, 1f, 0.58f))
            val sky = Brush.verticalGradient(colors.sky)
            val fadeDown = Brush.verticalGradient(0.35f to Color.Transparent, 0.75f to colors.fade.copy(alpha = 0.6f), 1f to colors.fade)
            val fadeSide = Brush.horizontalGradient(0.45f to Color.Transparent, 1f to colors.fade.copy(alpha = 0.8f))
            val sunCenter = Offset(w * 0.34f, h * 0.6f)
            val sunRadius = w * 0.068f

            onDrawBehind {
                drawRect(sky)
                drawCircle(colors.sun, sunRadius, sunCenter)
                drawPath(back, colors.back)
                drawPath(front, colors.front)
                drawRect(fadeDown)
                drawRect(fadeSide)
            }
        },
    )
}
