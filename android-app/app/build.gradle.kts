plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "org.tuuwanasavi.synthshai"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.tuuwanasavi.synthshai"
        minSdk = 26
        targetSdk = 35
        versionCode = 6
        versionName = "0.2.3.1"
    }

    buildTypes {
        create("staging") {
            initWith(getByName("debug"))
            applicationIdSuffix = ".staging"
            versionNameSuffix = "-signin"
            matchingFallbacks += "debug"
            resValue("string", "signin_origin", providers.gradleProperty("shaiSigninOrigin").orElse("").get())
            resValue("string", "signin_client", providers.gradleProperty("shaiGoogleWebClientId").orElse("355882138973-d0c984tl8mfeq9rf0bea4lrk252pon2v.apps.googleusercontent.com").get())
        }
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
    "stagingImplementation"("androidx.credentials:credentials:1.3.0")
    "stagingImplementation"("androidx.credentials:credentials-play-services-auth:1.3.0")
    "stagingImplementation"("com.google.android.libraries.identity.googleid:googleid:1.1.1")
    "testStagingImplementation"("org.json:json:20240303")
    testImplementation("junit:junit:4.13.2")
}

