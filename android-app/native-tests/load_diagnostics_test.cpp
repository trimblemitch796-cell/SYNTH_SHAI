#include "LoadDiagnostics.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

using shai::LoadDiagnostics;

int main() {
    LoadDiagnostics d;
    int tests = 0;
    auto has = [](const auto &report, const char *text) {
        return std::string(report.data()).find(text) != std::string::npos;
    };
    d.append("must not be retained");
    auto report = d.finish("Model loading");
    assert(has(report, "No warning/error message was emitted"));
    assert(!has(report, "must not be retained")); ++tests;

    d.begin();
    d.append("loader: failed to read tensor data\n");
    report = d.finish("Model loading");
    assert(has(report, "Model loading failed."));
    assert(has(report, "loader: failed to read tensor data\n")); ++tests;

    d.begin();
    d.append("warning\n");
    d.append("error\n");
    report = d.finish("Conversation initialization");
    assert(has(report, "Conversation initialization failed."));
    assert(has(report, "warning\nerror\n")); ++tests;

    d.begin();
    d.append(nullptr);
    d.append("");
    report = d.finish("Model loading");
    assert(has(report, "The cause is not established.")); ++tests;

    d.begin();
    d.append("\x1b[31m\xc3\xa9\r\n\t");
    report = d.finish("Model loading");
    assert(has(report, "[non-ASCII/control bytes replaced]"));
    assert(has(report, "?[31m???\n\t")); ++tests;

    d.begin();
    std::string exactly(LoadDiagnostics::capacity, 'x');
    d.append(exactly.c_str());
    report = d.finish("Model loading");
    assert(!has(report, "truncated"));
    assert(has(report, exactly.c_str())); ++tests;

    d.begin();
    std::string large(LoadDiagnostics::capacity * 3, 'x');
    large += "FINAL ERROR";
    d.append(large.c_str());
    report = d.finish("Model loading");
    assert(has(report, "[tail only; truncated]"));
    const std::string tail(report.data());
    assert(tail.substr(tail.size() - 11) == "FINAL ERROR");
    assert(std::strlen(report.data()) < report.size()); ++tests;

    d.append("post-failure message");
    report = d.finish("Model loading");
    assert(!has(report, "FINAL ERROR"));
    assert(!has(report, "post-failure message")); ++tests;

    d.begin();
    d.append("stale warning");
    d.clear();
    d.begin();
    report = d.finish("Model loading");
    assert(!has(report, "stale warning")); ++tests;

    {
        shai::LoadDiagnosticScope capture(d);
        d.append("successful initialization warning");
    }
    d.append("private prompt must not be captured");
    report = d.finish("Model loading");
    assert(!has(report, "successful initialization warning"));
    assert(!has(report, "private prompt")); ++tests;

    try {
        shai::LoadDiagnosticScope capture(d);
        d.append("exception warning");
        throw std::runtime_error("synthetic");
    } catch (const std::runtime_error &) {}
    report = d.finish("Model loading");
    assert(!has(report, "exception warning")); ++tests;

    d.begin();
    std::vector<std::thread> workers;
    for (int i = 0; i < 4; ++i) workers.emplace_back([&] {
        for (int j = 0; j < 1000; ++j) d.append("parallel error\n");
    });
    for (auto &worker : workers) worker.join();
    report = d.finish("Model loading");
    assert(has(report, "parallel error\n"));
    assert(has(report, "[tail only; truncated]"));
    assert(std::strlen(report.data()) < report.size()); ++tests;

    std::cout << "PASS: " << tests << " synthetic host diagnostic-buffer cases\n";
}
