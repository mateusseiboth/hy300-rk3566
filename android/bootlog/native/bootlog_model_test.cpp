/*
 * SPDX-FileCopyrightText: 2026 Mateus Seiboth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Testes do modelo do bootlog nativo (host): etapas pelos boot_progress_*, fim pelo
 * enable_screen, cores por prioridade e o limite de linhas.
 * Rodar: atest hy300-bootlog-model-test  (ou m hy300-bootlog-model-test e executar o binário)
 */
#include <gtest/gtest.h>

#include <chrono>
#include <cstdio>
#include <memory>
#include <thread>
#include <unistd.h>

#include "bootlog_model.h"

using hy300::bootlog::BootModel;
using hy300::bootlog::LineKind;
using hy300::bootlog::classifyLine;
using hy300::bootlog::stepProgress;
using hy300::bootlog::startLogReader;

TEST(BootModel, startsInKernelStage) {
    BootModel model;
    EXPECT_EQ(model.stage(), "kernel");
    EXPECT_EQ(model.progress(), 0);
    EXPECT_FALSE(model.screenEnabled());
}

TEST(BootModel, bootProgressEventsAdvanceStage) {
    BootModel model;
    model.addLine("I/boot_progress_preload_end(  123): 4567\n");
    EXPECT_EQ(model.stage(), "preload ok");
    EXPECT_EQ(model.progress(), 40);
    model.addLine("I/boot_progress_ams_ready(  456): 9999\n");
    EXPECT_EQ(model.stage(), "activity manager");
    EXPECT_EQ(model.progress(), 90);
}

TEST(BootModel, surfaceFlingerGivesFirstProgress) {
    BootModel model;
    model.addLine("I/SurfaceFlinger(  200): Enter boot animation\n");
    EXPECT_EQ(model.stage(), "surfaceflinger");
    EXPECT_EQ(model.progress(), 4);
}

TEST(BootModel, enableScreenEndsBoot) {
    BootModel model;
    model.addLine("I/boot_progress_enable_screen(  700): 21000\n");
    EXPECT_TRUE(model.screenEnabled());
    EXPECT_EQ(model.progress(), 100);
}

TEST(BootModel, keepsOnlyLastLinesWithoutNewlineOrTabs) {
    BootModel model(3);
    for (int i = 0; i < 5; ++i) model.addLine("I/Tag(1):\tlinha " + std::to_string(i) + "\n");
    auto lines = model.lastLines(10);
    ASSERT_EQ(lines.size(), 3u);
    EXPECT_EQ(lines.front().text, "I/Tag(1): linha 2");
    EXPECT_EQ(lines.back().text, "I/Tag(1): linha 4");
    EXPECT_EQ(model.lastLines(2).front().text, "I/Tag(1): linha 3");
}

TEST(ClassifyLine, priorities) {
    EXPECT_EQ(classifyLine("E/Tag(1): x"), LineKind::kError);
    EXPECT_EQ(classifyLine("F/Tag(1): x"), LineKind::kError);
    EXPECT_EQ(classifyLine("W/Tag(1): x"), LineKind::kWarning);
    EXPECT_EQ(classifyLine("I/kernel(  0): x"), LineKind::kKernel);
    EXPECT_EQ(classifyLine("I/boot_progress_start(  1): 5"), LineKind::kProgress);
    EXPECT_EQ(classifyLine("I/Zygote(  2): x"), LineKind::kRuntime);
    EXPECT_EQ(classifyLine("I/Tag(1): x"), LineKind::kNormal);
}

TEST(StepProgress, approachesTargetWithoutPassingIt) {
    EXPECT_EQ(stepProgress(0, 0), 0);
    EXPECT_EQ(stepProgress(0, 60), 10);
    EXPECT_EQ(stepProgress(98, 100), 99);
    EXPECT_EQ(stepProgress(100, 40), 100);
}

// No boot 2 o bootlog nativo deu SIGSEGV ao sair: a thread do logcat (desligada) usava o
// BootModel que vivia na pilha do main. O leitor agora é dono de uma referência ao modelo.
TEST(LogReader, keepsModelAliveAfterOwnerDropsIt) {
    int fds[2];
    ASSERT_EQ(pipe(fds), 0);
    FILE* in = fdopen(fds[0], "r");
    ASSERT_NE(in, nullptr);
    auto model = std::make_shared<BootModel>();
    std::weak_ptr<BootModel> watch = model;
    startLogReader(model, in);
    model.reset();
    EXPECT_FALSE(watch.expired());

    const char line[] = "I/boot_progress_enable_screen(  1): 2\n";
    ASSERT_EQ(write(fds[1], line, sizeof(line) - 1), static_cast<ssize_t>(sizeof(line) - 1));
    for (int i = 0; i < 200; ++i) {
        auto alive = watch.lock();
        if (alive && alive->screenEnabled()) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    auto alive = watch.lock();
    ASSERT_NE(alive, nullptr);
    EXPECT_TRUE(alive->screenEnabled());
    alive.reset();
    close(fds[1]);
    for (int i = 0; i < 200 && !watch.expired(); ++i)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    EXPECT_TRUE(watch.expired());  // fim do pipe: a thread sai e solta o modelo
}
