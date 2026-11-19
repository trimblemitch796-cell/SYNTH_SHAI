#include "ModelFilePreflight.h"
#include <cassert>
#include <sys/stat.h>
int main() {
    char path[] = "/tmp/shai-preflight-XXXXXX";
    const int fd = mkstemp(path);
    assert(fd >= 0);
    assert(write(fd, "GGUFrest", 8) == 8);
    assert(lseek(fd, 6, SEEK_SET) == 6);
    assert(shai::model_file_preflight(fd).empty());
    assert(shai::model_path_preflight(path).empty());
    assert(lseek(fd, 0, SEEK_CUR) == 6);
    assert(fchmod(fd, 0) == 0);
    char magic[4];
    assert(pread(fd, magic, 4, 0) == 4);
    // Root bypasses mode bits; this regression requires an unprivileged test user.
    if (geteuid() != 0) assert(shai::model_file_preflight(fd).find("errno 13") != std::string::npos);
    assert(fchmod(fd, 0600) == 0);
    assert(pwrite(fd, "BAD!", 4, 0) == 4);
    assert(shai::model_file_preflight(fd).find("GGUF header") != std::string::npos);
    close(fd); unlink(path);
    assert(shai::model_file_preflight(-1).find("cannot be reopened") != std::string::npos);
}
