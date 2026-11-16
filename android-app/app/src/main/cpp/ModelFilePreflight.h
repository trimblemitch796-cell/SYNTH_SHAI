#pragma once
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <unistd.h>

namespace shai {
// Match llama's pathname reopen, not merely reading the SAF-granted descriptor.
// Opening a new descriptor leaves the caller's offset and lifetime unchanged.
inline std::string model_path_preflight(const std::string &path) {
    const int fd = open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        const int error = errno;
        return "Model file cannot be reopened by the native engine (errno " +
            std::to_string(error) + ": " + std::strerror(error) +
            "). File verification succeeded separately; this does not establish a memory failure.";
    }
    unsigned char magic[4]{};
    ssize_t n;
    do { n = read(fd, magic, sizeof(magic)); } while (n < 0 && errno == EINTR);
    const int error = errno;
    close(fd);
    if (n < 0) return "Native model file read failed (errno " + std::to_string(error) + ").";
    if (n != 4 || std::memcmp(magic, "GGUF", 4) != 0)
        return "Native model file does not start with the GGUF header.";
    return {};
}
inline std::string model_file_preflight(int source_fd) {
    return model_path_preflight("/proc/self/fd/" + std::to_string(source_fd));
}
}
