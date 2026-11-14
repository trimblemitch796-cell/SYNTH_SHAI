#include <jni.h>
#include "llama.h"
#include <algorithm>
#include <memory>
#include <string>
#include <vector>

static void fail(JNIEnv *env, const char *message) {
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"), message);
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_org_tuuwanasavi_synthshai_LocalEngine_generate(
        JNIEnv *env, jobject, jint fd, jbyteArray input, jobject stop) {
    static const bool initialized = [] { llama_backend_init(); return true; }();
    (void)initialized;
    auto get = env->GetMethodID(env->GetObjectClass(stop), "get", "()Z");
    auto stopped = [&] { return env->CallBooleanMethod(stop, get) == JNI_TRUE; };
    std::string prompt(env->GetArrayLength(input), '\0');
    env->GetByteArrayRegion(input, 0, prompt.size(), reinterpret_cast<jbyte *>(prompt.data()));
    auto mp = llama_model_default_params();
    mp.n_gpu_layers = 0;
    auto path = "/proc/self/fd/" + std::to_string(fd);
    using Model = std::unique_ptr<llama_model, decltype(&llama_model_free)>;
    Model model(llama_model_load_from_file(path.c_str(), mp), llama_model_free);
    if (!model) { fail(env, "Model load failed. Check memory and the selected file."); return nullptr; }
    auto vocab = llama_model_get_vocab(model.get());
    std::vector<llama_token> tokens(928);
    auto count = llama_tokenize(vocab, prompt.data(), prompt.size(), tokens.data(), tokens.size(), false, true);
    if (count <= 0) { fail(env, "Context is full. Clear chat or shorten the message."); return nullptr; }
    auto cp = llama_context_default_params();
    cp.n_ctx = 1024;
    cp.n_batch = 128;
    cp.n_threads = cp.n_threads_batch = 3;
    using Context = std::unique_ptr<llama_context, decltype(&llama_free)>;
    Context ctx(llama_init_from_model(model.get(), cp), llama_free);
    if (!ctx) { fail(env, "Insufficient memory for the conversation."); return nullptr; }
    for (int offset = 0; offset < count && !stopped(); offset += 128) {
        if (llama_decode(ctx.get(), llama_batch_get_one(tokens.data()+offset, std::min(128, count-offset)))) {
            fail(env, "Prompt processing failed."); return nullptr;
        }
    }
    std::unique_ptr<llama_sampler, decltype(&llama_sampler_free)> sampler(llama_sampler_init_greedy(), llama_sampler_free);
    std::string out;
    for (int i = 0; i < 96 && !stopped(); ++i) {
        auto token = llama_sampler_sample(sampler.get(), ctx.get(), -1);
        if (llama_vocab_is_eog(vocab, token)) break;
        char piece[512];
        int size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, false);
        if (size < 0 || llama_decode(ctx.get(), llama_batch_get_one(&token, 1))) {
            fail(env, "Text generation failed."); return nullptr;
        }
        out.append(piece, size);
    }
    auto bytes = env->NewByteArray(out.size());
    if (bytes) env->SetByteArrayRegion(bytes, 0, out.size(), reinterpret_cast<const jbyte *>(out.data()));
    return bytes;
}
