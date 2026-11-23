/*
 * SPDX-FileCopyrightText: 2026 Mateus Seiboth
 * SPDX-License-Identifier: Apache-2.0
 */
#include "bootlog_model.h"

#include <algorithm>

namespace hy300::bootlog {

namespace {

struct Stage {
    const char* event;
    int progress;
    const char* name;
};

// Mesma tabela do Main.java.
constexpr Stage kStages[] = {
        {"boot_progress_start", 8, "zygote"},
        {"boot_progress_preload_start", 15, "preload"},
        {"boot_progress_preload_end", 40, "preload ok"},
        {"boot_progress_system_run", 50, "system_server"},
        {"boot_progress_pms_start", 58, "package manager"},
        {"boot_progress_pms_data_scan_start", 68, "scan /data"},
        {"boot_progress_pms_ready", 78, "pms ready"},
        {"boot_progress_ams_ready", 90, "activity manager"},
        {"boot_progress_enable_screen", 100, "enable screen"},
};

bool contains(const std::string& line, const char* needle) {
    return line.find(needle) != std::string::npos;
}

std::string clean(std::string line) {
    while (!line.empty() && (line.back() == '\n' || line.back() == '\r')) line.pop_back();
    std::replace(line.begin(), line.end(), '\t', ' ');
    return line;
}

}  // namespace

LineKind classifyLine(const std::string& line) {
    if (line.size() > 1 && line[1] == '/') {
        if (line[0] == 'E' || line[0] == 'F') return LineKind::kError;
        if (line[0] == 'W') return LineKind::kWarning;
    }
    if (contains(line, "/kernel") || contains(line, " kernel") || line.rfind("[k]", 0) == 0)
        return LineKind::kKernel;
    if (contains(line, "boot_progress")) return LineKind::kProgress;
    if (contains(line, "Zygote") || contains(line, "SystemServer")) return LineKind::kRuntime;
    return LineKind::kNormal;
}

int stepProgress(int shown, int target) {
    if (shown >= target) return shown;
    return std::min(target, shown + std::max(1, (target - shown) / 6));
}

void BootModel::addLine(std::string line) {
    line = clean(std::move(line));
    std::lock_guard<std::mutex> guard(lock_);
    applyStages(line);
    lines_.push_back(Line{line, classifyLine(line)});
    while (lines_.size() > maxLines_) lines_.pop_front();
}

void BootModel::applyStages(const std::string& line) {
    for (const Stage& s : kStages) {
        if (contains(line, s.event)) {
            progress_ = s.progress;
            stage_ = s.name;
        }
    }
    if (contains(line, "boot_progress_enable_screen")) screenEnabled_ = true;
    if (progress_ == 0 && contains(line, "SurfaceFlinger")) {
        progress_ = 4;
        stage_ = "surfaceflinger";
    }
}

std::vector<Line> BootModel::lastLines(size_t count) const {
    std::lock_guard<std::mutex> guard(lock_);
    const size_t start = lines_.size() > count ? lines_.size() - count : 0;
    return std::vector<Line>(lines_.begin() + start, lines_.end());
}

std::string BootModel::stage() const {
    std::lock_guard<std::mutex> guard(lock_);
    return stage_;
}

int BootModel::progress() const {
    std::lock_guard<std::mutex> guard(lock_);
    return progress_;
}

bool BootModel::screenEnabled() const {
    std::lock_guard<std::mutex> guard(lock_);
    return screenEnabled_;
}

}  // namespace hy300::bootlog
