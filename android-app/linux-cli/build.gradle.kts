plugins {
    id("org.jetbrains.kotlin.jvm")
    application
}

kotlin {
    jvmToolchain(17)
    // Share only the pure scripted JVM engine, not Android runtime/UI helpers.
    // Explicit inclusions prevent future Android files leaking into this source set.
    sourceSets.getByName("main").kotlin.apply {
        srcDir("../app/src/main/java")
        include("**/OfflineReplies.kt", "**/LinuxOfflineChat.kt")
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
