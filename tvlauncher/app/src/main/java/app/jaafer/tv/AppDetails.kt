package app.jaafer.tv

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val BannerShape = RoundedCornerShape(20.dp)

/** Shown when OK is held on an app: the design's details page, applied to an installed app. */
@Composable
@OptIn(ExperimentalLayoutApi::class)
fun AppDetails(
    app: AppEntry,
    folder: String?,
    onOpen: () -> Unit,
    onPin: () -> Unit,
    onSetFolder: (String?) -> Unit,
) {
    val context = LocalContext.current
    val version = remember(app.pkg) {
        runCatching { context.packageManager.getPackageInfo(app.pkg, 0).versionName }.getOrNull()
    }
    val first = remember { FocusRequester() }
    LaunchedEffect(app.pkg) { focusWhenReady(first) }
    var choosingFolder by remember { mutableStateOf(false) }
    val firstFolder = remember { FocusRequester() }
    LaunchedEffect(choosingFolder) { if (choosingFolder) focusWhenReady(firstFolder) }

    Box(Modifier.fillMaxSize().background(Scenes.Sea.fade).trapFocus()) {
        Scene(Scenes.Sea, Modifier.fillMaxSize())
        Row(
            Modifier.fillMaxSize().padding(horizontal = 60.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(48.dp),
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Txt("تطبيق", 12.sp, color = Palette.TextDim, weight = FontWeight.SemiBold)
                Txt(app.label, 52.sp, weight = FontWeight.Bold, maxLines = 2)
                Txt(
                    listOfNotNull(version?.let { "الإصدار $it" }, app.pkg).joinToString(" · "),
                    11.sp,
                    color = Palette.TextMuted,
                )
                FlowRow(
                    Modifier.padding(top = 12.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    PillButton("فتح", Icons.Play, Modifier.focusRequester(first), onClick = onOpen)
                    PillButton("إلى البداية", Icons.ToFront, onClick = onPin)
                    PillButton(folder ?: "مجلد", Icons.Folder) { choosingFolder = !choosingFolder }
                    PillButton("المعلومات", Icons.Info) { Actions.appInfo(context, app.pkg) }
                    PillButton("حذف", Icons.Trash) { Actions.uninstall(context, app.pkg) }
                }
                if (choosingFolder) {
                    Txt("اختر مجلداً", 12.sp, Modifier.padding(top = 8.dp), color = Palette.TextDim, weight = FontWeight.SemiBold)
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        FOLDER_NAMES.forEachIndexed { i, name ->
                            PillButton(
                                if (name == folder) "✓ $name" else name,
                                null,
                                if (i == 0) Modifier.focusRequester(firstFolder) else Modifier,
                            ) { onSetFolder(name) }
                        }
                        if (folder != null) PillButton("إخراج من المجلد", null) { onSetFolder(null) }
                    }
                }
            }
            Image(
                bitmap = app.banner,
                contentDescription = app.label,
                contentScale = ContentScale.Crop,
                modifier = Modifier.width(260.dp).aspectRatio(16f / 9f).shadow(30.dp, BannerShape).clip(BannerShape),
            )
        }
    }
}
