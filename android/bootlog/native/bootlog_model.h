/*
 * SPDX-FileCopyrightText: 2026 Mateus Seiboth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Estado do bootlog nativo, sem dependência do Android (testado no host): linhas do logcat,
 * etapa e progresso pelos eventos boot_progress_*, fim pelo enable_screen.
 */
#pragma once

#include <cstddef>
#include <deque>
#include <mutex>
#include <string>
#include <vector>

namespace hy300::bootlog {

enum class LineKind { kNormal, kError, kWarning, kKernel, kProgress, kRuntime };

struct Line {
    std::string text;
    LineKind kind;
};

LineKind classifyLine(const std::string& line);

// Anda 1/6 do que falta (no mínimo 1) sem passar do alvo; nunca volta.
int stepProgress(int shown, int target);

class BootModel {
  public:
    explicit BootModel(size_t maxLines = 400) : maxLines_(maxLines) {}

    void addLine(std::string line);
    std::vector<Line> lastLines(size_t count) const;
    std::string stage() const;
    int progress() const;
    bool screenEnabled() const;

  private:
    void applyStages(const std::string& line);

    mutable std::mutex lock_;
    size_t maxLines_;
    std::deque<Line> lines_;
    std::string stage_ = "kernel";
    int progress_ = 0;
    bool screenEnabled_ = false;
};

}  // namespace hy300::bootlog
