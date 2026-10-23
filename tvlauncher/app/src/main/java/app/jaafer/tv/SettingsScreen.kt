package app.jaafer.tv

import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
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

private class SettingItem(val label: String, val description: String, val icon: ImageVector, val color: Color, val action: String)

private val settingItems = listOf(
    SettingItem("عام", "الخيارات العامة للجهاز", Icons.Gear, Color(0xFF8E8E93), Settings.ACTION_SETTINGS),
    SettingItem("الشبكة والإنترنت", "Wi‑Fi والاتصال السلكي", Icons.Wifi, Color(0xFF1F6FEB), Settings.ACTION_WIFI_SETTINGS),
    SettingItem("الشاشة والصوت", "الدقة، HDR، ومخرج الصوت", Icons.Tv, Color(0xFFE8435A), Settings.ACTION_DISPLAY_SETTINGS),
    SettingItem("التطبيقات", "إدارة التطبيقات والأذونات والمساحة", Icons.Apps, Color(0xFF5E5CE6), Settings.ACTION_APPLICATION_SETTINGS),
    SettingItem("جهاز التحكم والملحقات", "إقران جهاز التحكم وسماعات البلوتوث", Icons.Remote, Color(0xFF30B0C7), Settings.ACTION_BLUETOOTH_SETTINGS),
    SettingItem("التاريخ والوقت", "المنطقة الزمنية وتنسيق الساعة", Icons.Clock, Color(0xFFF29D38), Settings.ACTION_DATE_SETTINGS),
    SettingItem("اللغة", "لغة الواجهة ولوحة المفاتيح", Icons.Globe, Color(0xFF34C759), Settings.ACTION_LOCALE_SETTINGS),
    SettingItem("تسهيلات الاستخدام", "الترجمة النصية، النص الكبير، وقارئ الشاشة", Icons.Person, Color(0xFF0A84FF), Settings.ACTION_ACCESSIBILITY_SETTINGS),
    SettingItem("شاشة التوقف", "اختر «$USER_NAME TV» شاشة توقف للتلفاز كله", Icons.Moon, Color(0xFF5E5CE6), Settings.ACTION_DREAM_SETTINGS),
    SettingItem("الشاشة الرئيسية", "اجعل «$USER_NAME TV» الشاشة الرئيسية للتلفاز", Icons.Home, Color(0xFFC46A52), Settings.ACTION_HOME_SETTINGS),
    SettingItem("حول الجهاز", "الطراز، الإصدار، والتحديثات", Icons.Info, Color(0xFF636366), Settings.ACTION_DEVICE_INFO_SETTINGS),
)

@Composable
fun SettingsScreen() {
    val context = LocalContext.current
    var selected by remember { mutableIntStateOf(0) }
    val first = remember { FocusRequester() }
    LaunchedEffect(Unit) { focusWhenReady(first) }

    Row(Modifier.fillMaxSize().background(Palette.SettingsBg).trapFocus()) {
        Column(Modifier.weight(1f).fillMaxHeight().padding(start = 60.dp, end = 40.dp, top = 40.dp)) {
            Txt("الإعدادات", 22.sp, Modifier.fillMaxWidth(), weight = FontWeight.Bold, align = TextAlign.Center)
            LazyColumn(
                contentPadding = PaddingValues(vertical = 20.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                itemsIndexed(settingItems) { index, item ->
                    FocusRow(
                        onClick = { Actions.settings(context, item.action) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(44.dp)
                            .then(if (index == 0) Modifier.focusRequester(first) else Modifier),
                        shape = RoundedCornerShape(11.dp),
                        idle = Palette.GlassLow,
                        scaleTo = 1.03f,
                        arrangement = Arrangement.SpaceBetween,
                        onFocused = { selected = index },
                    ) { focused ->
                        Txt(
                            item.label,
                            14.sp,
                            color = if (focused) Palette.SettingsBg else Color.White,
                            weight = if (focused) FontWeight.SemiBold else FontWeight.Medium,
                        )
                        Ico(Icons.Chevron, if (focused) Palette.SettingsBg else Palette.TextMuted, 11.dp)
                    }
                }
            }
        }

        val item = settingItems[selected]
        Column(
            Modifier.weight(1f).fillMaxHeight(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(18.dp, Alignment.CenterVertically),
        ) {
            Box(
                Modifier
                    .size(190.dp)
                    .shadow(30.dp, RoundedCornerShape(44.dp))
                    .clip(RoundedCornerShape(44.dp))
                    .background(item.color),
                contentAlignment = Alignment.Center,
            ) {
                Ico(item.icon, Color.White, 110.dp)
            }
            Txt(
                item.description,
                13.sp,
                Modifier.width(280.dp),
                color = Palette.TextDim,
                maxLines = 2,
                align = TextAlign.Center,
            )
        }
    }
}
