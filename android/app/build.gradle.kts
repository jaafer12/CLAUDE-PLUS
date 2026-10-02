plugins {
    id("com.android.application")
}

// Wraps web/app.html (the single source of the app UI) into a full HTML document
// and copies the bundled fonts, so the APK works fully offline.
abstract class BundleWebTask : DefaultTask() {
    @get:InputDirectory
    abstract val webDir: DirectoryProperty

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun bundle() {
        val src = webDir.get().asFile
        val out = outputDir.get().asFile
        out.deleteRecursively()
        File(out, "fonts").mkdirs()
        val body = File(src, "app.html").readLines()
            .filterNot { it.contains("fonts.googleapis.com") || it.contains("fonts.gstatic.com") }
            .joinToString("\n")
        File(out, "index.html").writeText(
            "<!doctype html>\n<html lang=\"ar\" dir=\"rtl\">\n<head>\n<meta charset=\"utf-8\">\n" +
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n" +
                "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
        )
        File(src, "fonts").listFiles { f -> f.extension == "woff2" }?.forEach {
            it.copyTo(File(out, "fonts/${it.name}"), overwrite = true)
        }
    }
}

val bundleWeb = tasks.register<BundleWebTask>("bundleWeb") {
    webDir.set(rootProject.file("../web"))
}

android {
    namespace = "app.kalimakalima"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.kalimakalima"
        minSdk = 26
        targetSdk = 35
        versionCode = (project.findProperty("vc") as String?)?.toIntOrNull() ?: 1
        versionName = "1.0.$versionCode"
    }

    signingConfigs {
        // A fixed key committed to the repo, so every CI build can update the installed app.
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        getByName("debug") {
            signingConfig = signingConfigs.getByName("debug")
        }
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

androidComponents {
    onVariants { variant ->
        variant.sources.assets?.addGeneratedSourceDirectory(bundleWeb, BundleWebTask::outputDir)
    }
}

dependencies {
    implementation("androidx.webkit:webkit:1.12.1")
}
