package app.jaafer.tv

import android.content.Context
import android.content.Intent
import android.content.pm.ResolveInfo
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.net.Uri
import android.provider.Settings
import android.widget.Toast
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.core.content.edit
import androidx.core.graphics.ColorUtils
import androidx.core.graphics.drawable.toBitmap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AppEntry(val pkg: String, val activity: String, val label: String, val banner: ImageBitmap)

private const val BANNER_W = 384
private const val BANNER_H = 216
private const val ICON = 112
private const val KEY_PINNED = "pinned"
private const val KEY_COUNT = "n_"
private const val KEY_FOLDER = "folder_"

val FOLDER_NAMES = listOf("أفلام", "مسلسلات", "أطفال", "رياضة", "موسيقى", "ألعاب", "أدوات")

class AppRepository(context: Context) {
    private val context = context.applicationContext
    private val pm = this.context.packageManager
    private val prefs = this.context.getSharedPreferences("launcher", Context.MODE_PRIVATE)

    // Banners are rendered once per app version, so returning to the home screen costs no drawing.
    private val cache = HashMap<String, Pair<Long, AppEntry>>()

    suspend fun load(): List<AppEntry> = withContext(Dispatchers.IO) {
        val found = LinkedHashMap<String, ResolveInfo>()
        for (category in listOf(Intent.CATEGORY_LEANBACK_LAUNCHER, Intent.CATEGORY_LAUNCHER)) {
            val query = Intent(Intent.ACTION_MAIN).addCategory(category)
            for (info in pm.queryIntentActivities(query, 0)) {
                val pkg = info.activityInfo.packageName
                if (pkg != context.packageName && pkg !in found) found[pkg] = info
            }
        }
        val entries = synchronized(cache) {
            cache.keys.retainAll(found.keys)
            found.values.map { entryFor(it) }
        }
        sorted(entries)
    }

    private fun entryFor(info: ResolveInfo): AppEntry {
        val ai = info.activityInfo
        val updated = runCatching { pm.getPackageInfo(ai.packageName, 0).lastUpdateTime }.getOrDefault(0L)
        cache[ai.packageName]?.let { (time, entry) -> if (time == updated && entry.activity == ai.name) return entry }
        val bitmap = renderBanner(info).also { it.prepareToDraw() }
        val entry = AppEntry(ai.packageName, ai.name, info.loadLabel(pm).toString(), bitmap.asImageBitmap())
        cache[ai.packageName] = updated to entry
        return entry
    }

    private fun renderBanner(info: ResolveInfo): Bitmap {
        val ai = info.activityInfo
        val banner = runCatching { ai.loadBanner(pm) ?: ai.applicationInfo.loadBanner(pm) }.getOrNull()
        if (banner != null) return banner.toBitmap(BANNER_W, BANNER_H, Bitmap.Config.ARGB_8888)

        // Phone apps have no TV banner: centre the icon on a tile tinted from its own colours.
        val icon = info.loadIcon(pm).toBitmap(ICON, ICON, Bitmap.Config.ARGB_8888)
        val average = Bitmap.createScaledBitmap(icon, 1, 1, true).getPixel(0, 0)
        val tint = ColorUtils.blendARGB(average or 0xFF000000.toInt(), android.graphics.Color.BLACK, 0.45f)
        val out = Bitmap.createBitmap(BANNER_W, BANNER_H, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(out)
        canvas.drawColor(tint)
        val left = (BANNER_W - ICON) / 2
        val top = (BANNER_H - ICON) / 2
        canvas.drawBitmap(icon, null, Rect(left, top, left + ICON, top + ICON), Paint(Paint.FILTER_BITMAP_FLAG))
        return out
    }

    private fun pinned(): List<String> = prefs.getString(KEY_PINNED, "").orEmpty().split(',').filter { it.isNotEmpty() }

    /** Pinned apps first, then the most opened, then by name. */
    private fun sorted(list: List<AppEntry>): List<AppEntry> {
        val pinned = pinned()
        return list.sortedWith(
            compareBy<AppEntry>(
                { pinned.indexOf(it.pkg).let { i -> if (i < 0) Int.MAX_VALUE else i } },
                { -prefs.getInt(KEY_COUNT + it.pkg, 0) },
                { it.label.lowercase() },
            ),
        )
    }

    fun pin(pkg: String) {
        prefs.edit { putString(KEY_PINNED, (listOf(pkg) + pinned().filter { it != pkg }).joinToString(",")) }
    }

    /** Package name to folder name, for every app that sits in a folder. */
    fun folders(): Map<String, String> = prefs.all.mapNotNull { (key, value) ->
        if (key.startsWith(KEY_FOLDER) && value is String) key.removePrefix(KEY_FOLDER) to value else null
    }.toMap()

    fun setFolder(pkg: String, folder: String?) {
        prefs.edit { if (folder == null) remove(KEY_FOLDER + pkg) else putString(KEY_FOLDER + pkg, folder) }
    }

    fun launch(from: Context, app: AppEntry): Boolean {
        val intent = pm.getLeanbackLaunchIntentForPackage(app.pkg)
            ?: pm.getLaunchIntentForPackage(app.pkg)
            ?: Intent(Intent.ACTION_MAIN).setClassName(app.pkg, app.activity)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
        return try {
            from.startActivity(intent)
            prefs.edit { putInt(KEY_COUNT + app.pkg, prefs.getInt(KEY_COUNT + app.pkg, 0) + 1) }
            true
        } catch (e: Exception) {
            Toast.makeText(from, "تعذّر فتح ${app.label}", Toast.LENGTH_SHORT).show()
            false
        }
    }
}

sealed interface HomeItem {
    val key: String
}

class AppItem(val app: AppEntry) : HomeItem {
    override val key get() = app.pkg
}

class FolderItem(val name: String, val apps: List<AppEntry>) : HomeItem {
    override val key get() = "folder:$name"
}

/** Apps in a folder collapse into one folder tile, placed where its highest-ranked app was. */
fun buildHomeItems(apps: List<AppEntry>, folders: Map<String, String>): List<HomeItem> {
    val members = apps.filter { it.pkg in folders }.groupBy { folders.getValue(it.pkg) }
    val placed = HashSet<String>()
    return apps.mapNotNull { app ->
        val folder = folders[app.pkg]
        when {
            folder == null -> AppItem(app)
            placed.add(folder) -> FolderItem(folder, members.getValue(folder))
            else -> null
        }
    }
}

/** Keeps the on-screen order stable on refresh: known apps stay put, new ones are appended. */
fun mergeApps(old: List<AppEntry>?, fresh: List<AppEntry>): List<AppEntry> {
    if (old == null) return fresh
    val byPkg = fresh.associateBy { it.pkg }
    val kept = old.mapNotNull { byPkg[it.pkg] }
    val known = kept.mapTo(HashSet()) { it.pkg }
    return kept + fresh.filter { it.pkg !in known }
}

/** System screens, each with fallbacks because TV vendors ship different settings apps. */
object Actions {
    private fun start(context: Context, vararg intents: Intent): Boolean {
        for (intent in intents) {
            try {
                context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return true
            } catch (e: Exception) {
            }
        }
        Toast.makeText(context, "هذا الخيار غير متاح على جهازك", Toast.LENGTH_SHORT).show()
        return false
    }

    fun settings(context: Context, action: String) = start(context, Intent(action), Intent(Settings.ACTION_SETTINGS))

    fun search(context: Context) = start(
        context,
        Intent(Intent.ACTION_ASSIST),
        Intent("android.search.action.GLOBAL_SEARCH"),
        Intent(Intent.ACTION_WEB_SEARCH),
    )

    fun voiceSearch(context: Context) = start(
        context,
        Intent(Intent.ACTION_VOICE_ASSIST),
        Intent(Intent.ACTION_ASSIST),
        Intent("android.speech.action.WEB_SEARCH"),
        Intent("android.search.action.GLOBAL_SEARCH"),
    )

    fun appInfo(context: Context, pkg: String) =
        start(context, Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$pkg")))

    fun uninstall(context: Context, pkg: String) = start(context, Intent(Intent.ACTION_DELETE, Uri.parse("package:$pkg")))
}
