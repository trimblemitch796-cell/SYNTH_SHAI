#pragma once
#include <memory>
#include <string>
#include <utility>

namespace shai {
// Caller serializes access. Holds weights only, never conversation context.
template<class T, class Deleter> class SingleModelCache {
    std::unique_ptr<T, Deleter> value_;
    std::string key_;
public:
    explicit SingleModelCache(Deleter deleter) : value_(nullptr, deleter) {}
    template<class Loader> T* get(const std::string& key, Loader load) {
        if (value_ && key_ == key) return value_.get();
        clear(); // Release the old allocation before loading another model.
        value_.reset(load());
        if (value_) key_ = key;
        return value_.get();
    }
    void clear() { value_.reset(); key_.clear(); }
};
}
