#pragma once

#include <array>
#include <cstddef>
#include <cstdio>
#include <mutex>

namespace shai {

// Memory-only diagnostics. No file, network, prompt or response logging.
// Keep only the tail, because the most specific load failure is often last.
class LoadDiagnostics {
public:
    static constexpr std::size_t capacity = 4096;
    using Report = std::array<char, capacity + 384>;

    void begin() {
        std::lock_guard<std::mutex> lock(mutex_);
        reset();
        active_ = true;
    }

    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        active_ = false;
        reset();
    }

    // The engine may call its logger from worker threads. Never throw through it.
    // Only ERROR/WARN messages during model/context initialization are passed in.
    void append(const char *text) noexcept {
        if (!text) return;
        try {
            std::lock_guard<std::mutex> lock(mutex_);
            if (!active_) return;
            for (const unsigned char *p = reinterpret_cast<const unsigned char *>(text); *p; ++p) {
                const bool safe = (*p >= 32 && *p <= 126) || *p == '\n' || *p == '\t';
                const char c = safe ? static_cast<char>(*p) : '?';
                sanitized_ |= !safe;
                buffer_[next_] = c;
                next_ = (next_ + 1) % capacity;
                if (size_ < capacity) ++size_;
                else truncated_ = true;
            }
        } catch (...) {
            // Logging must not cause a new exception in the native engine.
        }
    }

    // ASCII output is safe for JNI ThrowNew's modified-UTF-8 requirement.
    // No dynamic allocation is needed to build the native error report.
    Report finish(const char *stage) {
        std::lock_guard<std::mutex> lock(mutex_);
        active_ = false;
        Report result{};
        const int prefix = std::snprintf(result.data(), 256, "%s failed.\nEngine diagnostics%s%s:\n",
            stage, truncated_ ? " [tail only; truncated]" : "",
            sanitized_ ? " [non-ASCII/control bytes replaced]" : "");
        std::size_t at = prefix < 0 ? 0 : (static_cast<std::size_t>(prefix) < 256 ?
            static_cast<std::size_t>(prefix) : 255);
        if (size_ == 0) {
            std::snprintf(result.data() + at, result.size() - at,
                "No warning/error message was emitted. The cause is not established.");
        } else {
            const auto start = (next_ + capacity - size_) % capacity;
            for (std::size_t i = 0; i < size_; ++i) result[at++] = buffer_[(start + i) % capacity];
            result[at] = '\0';
        }
        reset();
        return result;
    }

private:
    void reset() {
        buffer_.fill('\0');
        size_ = next_ = 0;
        truncated_ = sanitized_ = false;
    }

    std::mutex mutex_;
    std::array<char, capacity> buffer_{};
    std::size_t size_ = 0;
    std::size_t next_ = 0;
    bool active_ = false;
    bool truncated_ = false;
    bool sanitized_ = false;
};

class LoadDiagnosticScope {
public:
    explicit LoadDiagnosticScope(LoadDiagnostics &diagnostics) : diagnostics_(diagnostics) {
        diagnostics_.begin();
    }
    ~LoadDiagnosticScope() { diagnostics_.clear(); }
    LoadDiagnosticScope(const LoadDiagnosticScope &) = delete;
    LoadDiagnosticScope &operator=(const LoadDiagnosticScope &) = delete;
private:
    LoadDiagnostics &diagnostics_;
};

} // namespace shai
