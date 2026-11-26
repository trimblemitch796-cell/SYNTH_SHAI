#include <jni.h>
#include "llama.h"
#include "LoadDiagnostics.h"
#include "ModelFilePreflight.h"
#include "SingleModelCache.h"
#include <atomic>
#include <chrono>
#include <algorithm>
#include <memory>
#include <string>
#include <vector>
#include <new>
#include <exception>

// The llama/ggml logger is global. Register it once with lifetime-stable storage.
// Serialize native calls so one request cannot receive another request's errors.
static shai::LoadDiagnostics load_diagnostics;
static std::mutex generation_mutex;
static shai::SingleModelCache<llama_model, decltype(&llama_model_free)> model_cache(llama_model_free);
static std::atomic<bool> release_requested{false};
struct ReleaseOnExit {
    ~ReleaseOnExit() { if (release_requested.load()) model_cache.clear(); }
};
static std::string logging_model_path; // Stable while the serialized native call is active.

static void engine_log(ggml_log_level level, const char *text, void *) noexcept {
    if (level == GGML_LOG_LEVEL_ERROR || level == GGML_LOG_LEVEL_WARN) {
        try {
            std::string safe(text ? text : "");
            if (!logging_model_path.empty()) {
                for (size_t pos = 0; (pos = safe.find(logging_model_path, pos)) != std::string::npos;) {
                    safe.replace(pos, logging_model_path.size(), "[private model]");
                    pos += 15;
                }
            }
            load_diagnostics.append(safe.c_str());
        } catch (...) { load_diagnostics.append("Engine diagnostic unavailable."); }
    }
}

static void fail(JNIEnv *env, const char *message) {
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"), message);
}

extern "C" JNIEXPORT void JNICALL
Java_org_tuuwanasavi_synthshai_LocalEngine_releaseModel(JNIEnv*, jobject) {
    release_requested.store(true);
    std::unique_lock<std::mutex> lock(generation_mutex, std::try_to_lock);
    if (lock.owns_lock()) model_cache.clear();
    // An active generation releases its context first, then cached weights on exit.
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_org_tuuwanasavi_synthshai_LocalEngine_generate(
        JNIEnv *env, jobject, jstring model_path, jbyteArray input, jobject stop) {
    try {
    std::unique_lock<std::mutex> generation_lock(generation_mutex, std::try_to_lock);
    if (!generation_lock.owns_lock()) {
        fail(env, "Another local generation is running. Stop it before retrying.");
        return nullptr;
    }
    if (release_requested.exchange(false)) model_cache.clear();
    ReleaseOnExit release_on_exit;
    const char *raw_path = env->GetStringUTFChars(model_path, nullptr);
    if (!raw_path) return nullptr;
    auto release_path = [&](const char *p) { env->ReleaseStringUTFChars(model_path, p); };
    std::unique_ptr<const char, decltype(release_path)> path_chars(raw_path, release_path);
    const std::string path(path_chars.get());
    path_chars.reset();
    logging_model_path = path;
    static const bool initialized = [] {
        llama_log_set(engine_log, nullptr);
        llama_backend_init();
        return true;
    }();
    (void)initialized;
    auto get = env->GetMethodID(env->GetObjectClass(stop), "get", "()Z");
    if (!get || env->ExceptionCheck()) return nullptr;
    auto stopped = [&] { return env->CallBooleanMethod(stop, get) == JNI_TRUE; };
    if (stopped()) return env->NewByteArray(0);
    if (env->GetArrayLength(input) > 131072) { fail(env, "Prompt is too long."); return nullptr; }
    std::string prompt(env->GetArrayLength(input), '\0');
    env->GetByteArrayRegion(input, 0, prompt.size(), reinterpret_cast<jbyte *>(prompt.data()));
    if (env->ExceptionCheck()) return nullptr;
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    const auto file_error = shai::model_path_preflight(path);
    if (!file_error.empty()) { fail(env, file_error.c_str()); return nullptr; }
    using Clock = std::chrono::steady_clock;
    auto milliseconds = [](Clock::time_point a, Clock::time_point b) {
        return std::chrono::duration_cast<std::chrono::milliseconds>(b - a).count();
    };
    const auto load_start = Clock::now();
    bool cache_hit = true;
    llama_model* model = nullptr;
    {
        shai::LoadDiagnosticScope capture(load_diagnostics);
        model = model_cache.get(path, [&] { cache_hit = false; return llama_model_load_from_file(path.c_str(), mp); });
        if (!model) {
            const auto report = load_diagnostics.finish("Model loading");
            std::string safe_report(report.data());
            for (size_t pos = 0; (pos = safe_report.find(path, pos)) != std::string::npos;) {
                safe_report.replace(pos, path.size(), "[private model]");
                pos += 15;
            }
            fail(env, safe_report.c_str());
            return nullptr;
        }
    }
    const auto load_end = Clock::now();
    auto vocab = llama_model_get_vocab(model);
    std::vector<llama_token> tokens(928);
    auto count = llama_tokenize(vocab, prompt.data(), prompt.size(), tokens.data(), tokens.size(), false, true);
    if (count <= 0) { fail(env, "Context is full. Clear chat or shorten the message."); return nullptr; }
    auto cp = llama_context_default_params();
    cp.n_ctx = 1024;
    cp.n_batch = 128;
    cp.n_threads = cp.n_threads_batch = 3;
    using Context = std::unique_ptr<llama_context, decltype(&llama_free)>;
    Context ctx(nullptr, llama_free);
    {
        shai::LoadDiagnosticScope capture(load_diagnostics);
        ctx.reset(llama_init_from_model(model, cp));
        if (!ctx) {
            const auto report = load_diagnostics.finish("Conversation initialization");
            std::string safe_report(report.data());
            for (size_t pos = 0; (pos = safe_report.find(path, pos)) != std::string::npos;) {
                safe_report.replace(pos, path.size(), "[private model]");
                pos += 15;
            }
            fail(env, safe_report.c_str());
            return nullptr;
        }
    }
    const auto setup_end = Clock::now();
    // Capture is disabled before processing any conversation text.
    for (int offset = 0; offset < count && !stopped(); offset += 128) {
        if (llama_decode(ctx.get(), llama_batch_get_one(tokens.data()+offset, std::min(128, count-offset)))) {
            fail(env, "Prompt processing failed."); return nullptr;
        }
    }
    const auto prefill_end = Clock::now();
    std::unique_ptr<llama_sampler, decltype(&llama_sampler_free)> sampler(llama_sampler_init_greedy(), llama_sampler_free);
    if (!sampler) { fail(env, "Text sampler could not be allocated."); return nullptr; }
    std::string out;
    std::string reason = "limit";
    int output_tokens = 0;
    for (int i = 0; i < 96 && !stopped(); ++i) {
        auto token = llama_sampler_sample(sampler.get(), ctx.get(), -1);
        if (llama_vocab_is_eog(vocab, token)) { reason = "end"; break; }
        char piece[512];
        int size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, false);
        if (size < 0 || llama_decode(ctx.get(), llama_batch_get_one(&token, 1))) {
            fail(env, "Text generation failed."); return nullptr;
        }
        out.append(piece, size);
        ++output_tokens;
    }
    const auto decode_end = Clock::now();
    if (stopped()) reason = "stopped";
    out = "SHAI1|" + reason + "|" + std::to_string(milliseconds(load_start, load_end)) +
        "|" + std::to_string(milliseconds(load_end, setup_end)) +
        "|" + std::to_string(milliseconds(setup_end, prefill_end)) +
        "|" + std::to_string(milliseconds(prefill_end, decode_end)) +
        "|" + std::to_string(count) + "|" + std::to_string(output_tokens) +
        "|" + (cache_hit ? "1" : "0") + "\n" + out;
    auto bytes = env->NewByteArray(out.size());
    if (bytes) env->SetByteArrayRegion(bytes, 0, out.size(), reinterpret_cast<const jbyte *>(out.data()));
    return bytes;
    } catch (const std::bad_alloc &) {
        if (!env->ExceptionCheck()) fail(env, "Native memory allocation failed. Close other apps and try a shorter message.");
    } catch (const std::exception &) {
        if (!env->ExceptionCheck()) fail(env, "The native engine reported an unexpected error. No response was produced.");
    } catch (...) {
        if (!env->ExceptionCheck()) fail(env, "The native engine could not complete generation.");
    }
    return nullptr;
}
