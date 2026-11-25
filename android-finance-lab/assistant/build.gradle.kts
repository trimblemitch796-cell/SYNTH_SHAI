plugins { id("com.android.application") }
android {
    namespace = "org.tuuwanasavi.financelab.assistant"
    compileSdk = 35
    defaultConfig {
        applicationId = "org.tuuwanasavi.financelab.assistant"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "0.1-mock-only"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
