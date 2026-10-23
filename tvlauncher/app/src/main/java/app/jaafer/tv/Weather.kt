package app.jaafer.tv

import android.content.Context
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.graphicsLayer
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
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.Locale
import kotlin.math.roundToInt

/** One forecast day; [date] is ISO yyyy-MM-dd in the location's own time zone. */
class DayForecast(val date: String, val code: Int, val high: Int, val low: Int)

class Weather(
    val temp: Int,
    val code: Int,
    val isDay: Boolean,
    val high: Int,
    val low: Int,
    val city: String,
    val days: List<DayForecast> = emptyList(),
) {
    fun toJson(): String = JSONObject()
        .put("temp", temp).put("code", code).put("day", isDay)
        .put("high", high).put("low", low).put("city", city)
        .put("days", JSONArray(days.map { JSONObject().put("date", it.date).put("code", it.code).put("high", it.high).put("low", it.low) }))
        .toString()

    companion object {
        fun fromJson(s: String): Weather? = runCatching {
            val o = JSONObject(s)
            val days = o.optJSONArray("days")?.let { a ->
                (0 until a.length()).map { i ->
                    val d = a.getJSONObject(i)
                    DayForecast(d.getString("date"), d.getInt("code"), d.getInt("high"), d.getInt("low"))
                }
            }.orEmpty()
            Weather(o.getInt("temp"), o.getInt("code"), o.getBoolean("day"), o.getInt("high"), o.getInt("low"), o.getString("city"), days)
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
                    "&daily=weather_code,temperature_2m_max,temperature_2m_min&forecast_days=6&timezone=auto",
            )
            val current = w.getJSONObject("current")
            val daily = w.getJSONObject("daily")
            val dates = daily.getJSONArray("time")
            val codes = daily.getJSONArray("weather_code")
            val highs = daily.getJSONArray("temperature_2m_max")
            val lows = daily.getJSONArray("temperature_2m_min")
            val days = (0 until dates.length()).map { i ->
                DayForecast(dates.getString(i), codes.optInt(i), highs.optDouble(i).roundToInt(), lows.optDouble(i).roundToInt())
            }
            Weather(
                temp = current.getDouble("temperature_2m").roundToInt(),
                code = current.getInt("weather_code"),
                isDay = current.optInt("is_day", 1) == 1,
                high = highs.getDouble(0).roundToInt(),
                low = lows.getDouble(0).roundToInt(),
                city = city,
                days = days,
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

private fun iconFor(code: Int, isDay: Boolean): ImageVector = when (code) {
    0, 1 -> if (isDay) Icons.Sun else Icons.Moon
    2 -> if (isDay) Icons.CloudSun else Icons.Cloud
    3, 45, 48 -> Icons.Cloud
    in 51..67, in 80..82 -> Icons.Rain
    in 71..77, 85, 86 -> Icons.Snow
    in 95..99 -> Icons.Storm
    else -> Icons.Cloud
}

private val arabic: Locale = Locale.forLanguageTag("ar")
private val arabicNumbers: NumberFormat = NumberFormat.getIntegerInstance(arabic)

private fun degrees(t: Int) = arabicNumbers.format(t.toLong()) + "°"

private fun weekday(isoDate: String): String = runCatching {
    val date = SimpleDateFormat("yyyy-MM-dd", Locale.US).parse(isoDate)!!
    SimpleDateFormat("EEEE", arabic).format(date)
}.getOrDefault(isoDate)

/**
 * The large clock and weather that sit in the open sky on the left of the home screen.
 * With [onWeatherClick] the weather part can be focused and opens the forecast.
 */
@Composable
fun ClockWeather(
    now: Long,
    weather: Weather?,
    modifier: Modifier = Modifier,
    onWeatherFocused: () -> Unit = {},
    onWeatherClick: (() -> Unit)? = null,
) {
    Column(modifier, horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Txt(formatTime(now), 60.sp, weight = FontWeight.SemiBold)
        Txt(formatDate(now), 15.sp, color = Palette.TextDim, weight = FontWeight.Medium)
        if (weather != null) WeatherBlock(weather, onWeatherFocused, onWeatherClick)
    }
}

@Composable
private fun WeatherBlock(weather: Weather, onWeatherFocused: () -> Unit, onWeatherClick: (() -> Unit)?) {
    var focused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(if (focused) 1.05f else 1f, tween(120), label = "weather")
    val shape = RoundedCornerShape(16.dp)
    Column(
        Modifier
            .padding(top = 6.dp)
            .graphicsLayer { scaleX = scale; scaleY = scale }
            .clip(shape)
            .background(if (focused) Palette.Glass else Color.Transparent)
            .then(
                if (onWeatherClick == null) Modifier
                else Modifier
                    .onFocusChanged {
                        focused = it.isFocused
                        if (it.isFocused) onWeatherFocused()
                    }
                    .tvClick(onClick = onWeatherClick),
            )
            .padding(horizontal = 12.dp, vertical = 6.dp),
        horizontalAlignment = Alignment.End,
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Ico(iconFor(weather.code, weather.isDay), Color.White, 30.dp)
            Txt(degrees(weather.temp), 30.sp, weight = FontWeight.SemiBold)
            Txt(describe(weather.code), 15.sp, color = Palette.TextDim, weight = FontWeight.Medium)
        }
        val range = "العظمى ${degrees(weather.high)} · الصغرى ${degrees(weather.low)}"
        Txt(if (weather.city.isBlank()) range else "${weather.city} · $range", 12.sp, color = Palette.TextMuted)
        if (focused) Txt("اضغط «موافق» لتوقعات الأيام القادمة", 11.sp, color = Palette.TextDim)
    }
}

/** The next five days, opened from the weather on the home screen. */
@Composable
fun ForecastPanel(weather: Weather, onClose: () -> Unit) {
    val close = remember { FocusRequester() }
    LaunchedEffect(Unit) { focusWhenReady(close) }
    val days = weather.days.drop(1).take(5)
    Box(Modifier.fillMaxSize().background(Color(0xB3000000)).trapFocus(), contentAlignment = Alignment.Center) {
        Column(
            Modifier
                .shadow(30.dp, RoundedCornerShape(26.dp))
                .clip(RoundedCornerShape(26.dp))
                .background(Palette.Panel)
                .padding(horizontal = 36.dp, vertical = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(22.dp),
        ) {
            Txt(
                if (weather.city.isBlank()) "توقعات الطقس" else "توقعات الطقس · ${weather.city}",
                20.sp,
                weight = FontWeight.Bold,
            )
            if (days.isEmpty()) {
                Txt("التوقعات غير متاحة الآن", 14.sp, color = Palette.TextDim)
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                    for (day in days) {
                        Column(
                            Modifier
                                .width(104.dp)
                                .clip(RoundedCornerShape(18.dp))
                                .background(Palette.GlassLow)
                                .padding(vertical = 16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Txt(weekday(day.date), 13.sp, weight = FontWeight.SemiBold)
                            Ico(iconFor(day.code, true), Color.White, 34.dp)
                            Txt(describe(day.code), 11.sp, color = Palette.TextDim)
                            Txt(degrees(day.high), 22.sp, weight = FontWeight.SemiBold)
                            Txt(degrees(day.low), 14.sp, color = Palette.TextMuted)
                        }
                    }
                }
            }
            PillButton("إغلاق", null, Modifier.focusRequester(close), onClick = onClose)
        }
    }
}
