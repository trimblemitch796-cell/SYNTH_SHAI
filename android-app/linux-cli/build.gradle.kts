plugins {
    id("org.jetbrains.kotlin.jvm")
    application
}

kotlin {
    jvmToolchain(17)
    // Reuse the exact JVM-compatible offline response engine shipped in the APK.
    // MainActivity.kt requires Android APIs and is deliberately excluded.
    sourceSets.getByName("main").kotlin.apply {
        srcDir("../app/src/main/java")
        exclude("**/MainActivity.kt")
    }
}

application {
    mainClass.set("org.tuuwanasavi.synthshai.LinuxOfflineChatKt")
    applicationName = "synth-shai-offline"
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    useJUnit()
}
