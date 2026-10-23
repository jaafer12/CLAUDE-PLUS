package app.jaafer.tv

import android.media.AudioManager
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val PanelShape = RoundedCornerShape(22.dp)

@Composable
fun ControlCenter(onOpenSettings: () -> Unit, onScreensaver: () -> Unit) {
    val context = LocalContext.current
    val now = rememberNow()
    val first = remember { FocusRequester() }
    LaunchedEffect(Unit) { focusWhenReady(first) }

    val audio = remember { context.getSystemService(AudioManager::class.java) }
    val maxVolume = remember { audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC).coerceAtLeast(1) }
    var volume by remember { mutableIntStateOf(audio.getStreamVolume(AudioManager.STREAM_MUSIC)) }
    fun adjust(direction: Int) {
        audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, direction, 0)
        volume = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
    }

    Box(Modifier.fillMaxSize().background(Color(0x99000000))) {
        Column(
            Modifier
                .align(Alignment.CenterEnd)
                .padding(24.dp)
                .width(300.dp)
                .fillMaxHeight()
                .shadow(30.dp, PanelShape)
                .clip(PanelShape)
                .background(Palette.Panel)
                .trapFocus()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(verticalAlignment = Alignment.Bottom) {
                Txt(formatTime(now), 32.sp, weight = FontWeight.SemiBold)
                Spacer(Modifier.weight(1f))
                Txt(formatDate(now), 11.sp, color = Palette.TextDim)
            }

            Txt("الملف الشخصي", 10.sp, color = Palette.TextMuted, weight = FontWeight.SemiBold)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Avatar(42.dp, ring = true)
                Column {
                    Txt(USER_NAME, 15.sp, weight = FontWeight.SemiBold)
                    Txt("المستخدم الحالي", 11.sp, color = Palette.TextMuted)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ControlTile(Icons.Power, "شاشة التوقف", Modifier.weight(1f).focusRequester(first)) { onScreensaver() }
                ControlTile(Icons.Wifi, "الشبكة", Modifier.weight(1f)) {
                    Actions.settings(context, android.provider.Settings.ACTION_WIFI_SETTINGS)
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ControlTile(Icons.Search, "البحث", Modifier.weight(1f)) { Actions.search(context) }
                ControlTile(Icons.Gear, "الإعدادات", Modifier.weight(1f), onOpenSettings)
            }

            Txt("الصوت", 10.sp, color = Palette.TextMuted, weight = FontWeight.SemiBold)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                RoundIconButton(Icons.Minus, "خفض الصوت") { adjust(AudioManager.ADJUST_LOWER) }
                Box(Modifier.weight(1f).height(30.dp).clip(RoundedCornerShape(15.dp)).background(Palette.Glass)) {
                    Box(
                        Modifier
                            .fillMaxHeight()
                            .fillMaxWidth(volume.toFloat() / maxVolume)
                            .background(Color(0xD9FFFFFF)),
                    )
                    Box(Modifier.align(Alignment.CenterStart).padding(start = 10.dp)) {
                        Ico(Icons.Volume, if (volume > 0) Palette.Bg else Color.White, 14.dp)
                    }
                }
                RoundIconButton(Icons.Plus, "رفع الصوت") { adjust(AudioManager.ADJUST_RAISE) }
            }

            Spacer(Modifier.weight(1f))
            Txt(
                "اضغط «رجوع» للإغلاق",
                11.sp,
                Modifier.fillMaxWidth(),
                color = Palette.TextMuted,
                align = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun ControlTile(icon: ImageVector, label: String, modifier: Modifier, onClick: () -> Unit) {
    FocusRow(
        onClick,
        modifier.height(64.dp),
        shape = RoundedCornerShape(14.dp),
        scaleTo = 1.04f,
        contentPadding = PaddingValues(horizontal = 14.dp),
    ) { focused ->
        val fg = if (focused) Palette.Bg else Color.White
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Ico(icon, fg, 18.dp)
            Txt(label, 12.sp, color = fg, weight = FontWeight.SemiBold)
        }
    }
}
