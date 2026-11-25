import java.security.MessageDigest

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Phone builds remain ARM64; emulator CI selects its matching native ABI.
val shaiAbi = providers.gradleProperty("shaiAbi").getOrElse("arm64-v8a")
require(shaiAbi in setOf("arm64-v8a", "x86_64")) { "Unsupported SHAI ABI" }

android {
    namespace = "org.tuuwanasavi.synthshai"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.tuuwanasavi.synthshai"
        minSdk = 26
        targetSdk = 35
        versionCode = 14
        versionName = "0.3.8-repetition-repair"
        applicationIdSuffix = ".localchat.optimized037"
        ndk { abiFilters += shaiAbi }
        externalNativeBuild { cmake { arguments += "-DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON" } }
    }

    ndkVersion = "27.2.12479018"
    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    testImplementation("junit:junit:4.13.2")
}

// Bundle exact source inputs at build time; never include private device files.
val sourceInputs = listOf(
    "src/main/java/org/tuuwanasavi/synthshai/LocalEngine.kt",
    "src/main/java/org/tuuwanasavi/synthshai/ChatHistoryCodec.kt",
    "src/main/java/org/tuuwanasavi/synthshai/MainActivity.kt",
    "src/main/cpp/chat.cpp"
)
val sourceAssets = layout.buildDirectory.dir("generated/sourceReaderAssets")
val bundleReadOnlySource by tasks.registering {
    inputs.files(sourceInputs.map { file(it) })
    outputs.dir(sourceAssets)
    doLast {
        val target = sourceAssets.get().dir("source_reader").asFile
        target.deleteRecursively()
        target.mkdirs()
        sourceInputs.forEach { path ->
            val input = file(path)
            val bytes = input.readBytes()
            require(bytes.size <= 65536)
            target.resolve(input.name).writeBytes(bytes)
            val hash = MessageDigest.getInstance("SHA-256").digest(bytes)
                .joinToString("") { "%02x".format(it) }
            target.resolve(input.name + ".sha256").writeText(hash)
        }
    }
}
android.sourceSets.getByName("main").assets.srcDir(sourceAssets)
tasks.named("preBuild").configure { dependsOn(bundleReadOnlySource) }
