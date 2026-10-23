package app.jaafer.tv

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.edit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.NumberFormat
import java.util.Locale
import kotlin.math.roundToInt

class Weather(val temp: Int, val code: Int, val isDay: Boolean, val high: Int, val low: Int, val city: String) {
    fun toJson(): String = JSONObject()
        .put("temp", temp).put("code", code).put("day", isDay)
        .put("high", high).put("low", low).put("city", city)
        .toString()

    companion object {
        fun fromJson(s: String): Weather? = runCatching {
            val o = JSONObject(s)
            Weather(o.getInt("temp"), o.getInt("code"), o.getBoolean("day"), o.getInt("high"), o.getInt("low"), o.getString("city"))
        }.getOrNull()
    }
}

private const val REFRESH_MS = 30 * 60 * 1000L
private const val LOCATION_MAX_AGE_MS = 24 * 60 * 60 * 1000L

/**
 * Weather from Open-Meteo (free, no key). TVs have no GPS, so the location comes from the
 * network's public IP and is cached for a day; the last reading is shown instantly at start.
 */
object WeatherSource {
    private fun prefs(context: Context) = context.getSharedPreferences("weather", Context.MODE_PRIVATE)

    fun cached(context: Context): Weather? = prefs(context).getString("last", null)?.let(Weather::fromJson)

    suspend fun fetch(context: Context): Weather? = withContext(Dispatchers.IO) {
        runCatching {
            val (lat, lon, city) = location(context) ?: return@runCatching null
            val w = get(
                "https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon" +
                    "&current=temperature_2m,weather_code,is_day" +
                    "&daily=temperature_2m_max,temperature_2m_min&forecast_days=1&timezone=auto",
            )
            val current = w.getJSONObject("current")
            val daily = w.getJSONObject("daily")
            Weather(
                temp = current.getDouble("temperature_2m").roundToInt(),
                code = current.getInt("weather_code"),
                isDay = current.optInt("is_day", 1) == 1,
                high = daily.getJSONArray("temperature_2m_max").getDouble(0).roundToInt(),
                low = daily.getJSONArray("temperature_2m_min").getDouble(0).roundToInt(),
                city = city,
            ).also { prefs(context).edit { putString("last", it.toJson()) } }
        }.getOrNull()
    }

    private fun location(context: Context): Triple<Double, Double, String>? {
        val p = prefs(context)
        if (System.currentTimeMillis() - p.getLong("loc_at", 0) < LOCATION_MAX_AGE_MS && p.contains("lat")) {
            return Triple(p.getFloat("lat", 0f).toDouble(), p.getFloat("lon", 0f).toDouble(), p.getString("city", "").orEmpty())
        }
        val found = runCatching {
            val o = get("https://ipwho.is/")
            if (!o.optBoolean("success", false)) error("lookup failed")
            Triple(o.getDouble("latitude"), o.getDouble("longitude"), o.optString("city"))
        }.recoverCatching {
            val o = get("https://ipapi.co/json/")
            Triple(o.getDouble("latitude"), o.getDouble("longitude"), o.optString("city"))
        }.getOrNull() ?: return null
        p.edit {
            putFloat("lat", found.first.toFloat())
            putFloat("lon", found.second.toFloat())
            putString("city", found.third)
            putLong("loc_at", System.currentTimeMillis())
        }
        return found
    }

    private fun get(url: String): JSONObject {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 8000
        conn.readTimeout = 8000
        try {
            return JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
        } finally {
            conn.disconnect()
        }
    }
}

@Composable
fun rememberWeather(): Weather? {
    val context = LocalContext.current
    val weather by produceState(WeatherSource.cached(context)) {
        while (true) {
            WeatherSource.fetch(context)?.let { value = it }
            delay(REFRESH_MS)
        }
    }
    return weather
}

// WMO weather codes, as used by Open-Meteo.
private fun describe(code: Int): String = when (code) {
    0 -> "صافٍ"
    1 -> "صافٍ غالباً"
    2 -> "غائم جزئياً"
    3 -> "غائم"
    45, 48 -> "ضباب"
    in 51..57 -> "رذاذ"
    in 61..67, in 80..82 -> "مطر"
    in 71..77, 85, 86 -> "ثلج"
    in 95..99 -> "عاصفة رعدية"
    else -> "—"
}

private fun iconFor(w: Weather): ImageVector = when (w.code) {
    0, 1 -> if (w.isDay) Icons.Sun else Icons.Moon
    2 -> if (w.isDay) Icons.CloudSun else Icons.Cloud
    3, 45, 48 -> Icons.Cloud
    in 51..67, in 80..82 -> Icons.Rain
    in 71..77, 85, 86 -> Icons.Snow
    in 95..99 -> Icons.Storm
    else -> Icons.Cloud
}

private val arabicNumbers: NumberFormat = NumberFormat.getIntegerInstance(Locale.forLanguageTag("ar"))

private fun degrees(t: Int) = arabicNumbers.format(t.toLong()) + "°"

/** The large clock and weather that sit in the open sky on the left of the home screen. */
@Composable
fun ClockWeather(now: Long, weather: Weather?, modifier: Modifier = Modifier) {
    Column(modifier, horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Txt(formatTime(now), 64.sp, weight = FontWeight.SemiBold)
        Txt(formatDate(now), 15.sp, color = Palette.TextDim, weight = FontWeight.Medium)
        if (weather != null) {
            Row(
                Modifier.padding(top = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Ico(iconFor(weather), Color.White, 30.dp)
                Txt(degrees(weather.temp), 30.sp, weight = FontWeight.SemiBold)
                Txt(describe(weather.code), 15.sp, color = Palette.TextDim, weight = FontWeight.Medium)
            }
            val range = "العظمى ${degrees(weather.high)} · الصغرى ${degrees(weather.low)}"
            Txt(if (weather.city.isBlank()) range else "${weather.city} · $range", 12.sp, color = Palette.TextMuted)
        }
    }
}
