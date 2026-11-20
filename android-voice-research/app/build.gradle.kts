plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
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
        versionCode = 6
        versionName = "0.9-reviewed-qwen"
        applicationIdSuffix = ".localchat.reviewedqwen09"
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
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
