/*
 * SPDX-FileCopyrightText: 2026 Mateus Seiboth
 * SPDX-License-Identifier: Apache-2.0
 *
 * Animação de boot com log ao vivo, versão nativa (C++) para o LineageOS 24 do HY300.
 * Mesmo visual do Main.java (logcat -b all ao vivo, cores por prioridade, tempo desde o boot,
 * etapa atual, barra de progresso pelos boot_progress_*, logo no canto), mas sem ART: desenha
 * assim que o SurfaceFlinger sobe, numa camada SurfaceControl, com FreeType e libpng direto no
 * buffer (CPU).
 *
 * Uso: hy300-bootlog <largura> <altura> <logo.png> [--test]
 * Sai em boot_progress_enable_screen, na transição 0->1 de service.bootanim.exit ou em 180 s
 * (15 s com --test) pelo relógio monotônico. Cria /dev/.bootlog_ready no primeiro quadro.
 * Código de saída != 0 = não conseguiu desenhar (o bootlog.sh cai na animação padrão).
 */
#include <android-base/properties.h>
#include <android/native_window.h>
#include <binder/ProcessState.h>
#include <gui/Surface.h>
#include <gui/SurfaceComposerClient.h>
#include <gui/SurfaceControl.h>
#include <png.h>
#include <ui/PixelFormat.h>
#include <utils/SystemClock.h>

#include <ft2build.h>
#include FT_FREETYPE_H

#include <fcntl.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <deque>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "bootlog_model.h"

using namespace android;
using hy300::bootlog::BootModel;

namespace {

constexpr int kLogoSize = 150;
constexpr int64_t kFrameMs = 40;

struct Rgb {
    uint8_t r, g, b;
};

struct Canvas {
    uint32_t* pixels;
    int width, height, stride;

    void fill(int x0, int y0, int x1, int y1, Rgb c) {
        x0 = std::max(x0, 0), y0 = std::max(y0, 0);
        x1 = std::min(x1, width), y1 = std::min(y1, height);
        const uint32_t v = 0xff000000u | (c.b << 16) | (c.g << 8) | c.r;
        for (int y = y0; y < y1; ++y) std::fill(pixels + y * stride + x0, pixels + y * stride + x1, v);
    }

    void blend(int x, int y, Rgb c, uint8_t alpha) {
        if (x < 0 || y < 0 || x >= width || y >= height || alpha == 0) return;
        uint32_t& p = pixels[y * stride + x];
        auto mix = [alpha](uint32_t dst, uint32_t src) { return (src * alpha + dst * (255 - alpha)) / 255; };
        const uint32_t r = mix(p & 0xff, c.r), g = mix((p >> 8) & 0xff, c.g), b = mix((p >> 16) & 0xff, c.b);
        p = 0xff000000u | (b << 16) | (g << 8) | r;
    }
};

struct Glyph {
    int left, top, advance, width, rows;
    std::vector<uint8_t> coverage;
};

class Font {
  public:
    bool open(FT_Library lib, const char* path, int pixels) {
        if (FT_New_Face(lib, path, 0, &face_) != 0) return false;
        FT_Set_Pixel_Sizes(face_, 0, pixels);
        lineHeight_ = static_cast<int>(face_->size->metrics.height >> 6);
        return true;
    }

    int lineHeight() const { return lineHeight_; }

    int measure(const std::string& text) {
        int w = 0;
        for (unsigned char ch : text) w += glyph(ch).advance;
        return w;
    }

    void draw(Canvas& canvas, int x, int baseline, const std::string& text, Rgb color, int maxChars = 1 << 30) {
        int drawn = 0;
        for (unsigned char ch : text) {
            if (drawn++ >= maxChars || x >= canvas.width) break;
            const Glyph& g = glyph(ch);
            for (int row = 0; row < g.rows; ++row)
                for (int col = 0; col < g.width; ++col)
                    canvas.blend(x + g.left + col, baseline - g.top + row, color, g.coverage[row * g.width + col]);
            x += g.advance;
        }
    }

  private:
    const Glyph& glyph(unsigned char ch) {
        auto it = cache_.find(ch);
        if (it != cache_.end()) return it->second;
        Glyph g{0, 0, 0, 0, 0, {}};
        if (FT_Load_Char(face_, ch < 0x80 ? ch : '?', FT_LOAD_RENDER) == 0) {
            const FT_Bitmap& bmp = face_->glyph->bitmap;
            g = Glyph{face_->glyph->bitmap_left, face_->glyph->bitmap_top,
                      static_cast<int>(face_->glyph->advance.x >> 6), static_cast<int>(bmp.width),
                      static_cast<int>(bmp.rows), {}};
            g.coverage.resize(bmp.width * bmp.rows);
            for (unsigned row = 0; row < bmp.rows; ++row)
                memcpy(&g.coverage[row * bmp.width], bmp.buffer + row * bmp.pitch, bmp.width);
        }
        return cache_.emplace(ch, std::move(g)).first->second;
    }

    FT_Face face_ = nullptr;
    int lineHeight_ = 16;
    std::map<unsigned char, Glyph> cache_;
};

struct Image {
    int width = 0, height = 0;
    std::vector<uint8_t> rgba;
};

bool loadPng(const char* path, Image* out) {
    png_image image;
    memset(&image, 0, sizeof(image));
    image.version = PNG_IMAGE_VERSION;
    if (!png_image_begin_read_from_file(&image, path)) return false;
    image.format = PNG_FORMAT_RGBA;
    out->width = image.width;
    out->height = image.height;
    out->rgba.resize(PNG_IMAGE_SIZE(image));
    return png_image_finish_read(&image, nullptr, out->rgba.data(), 0, nullptr) != 0;
}

void drawLogo(Canvas& canvas, const Image& logo, int x0, int y0, int size) {
    if (logo.width == 0) return;
    for (int y = 0; y < size; ++y)
        for (int x = 0; x < size; ++x) {
            const uint8_t* px = &logo.rgba[((y * logo.height / size) * logo.width + x * logo.width / size) * 4];
            canvas.blend(x0 + x, y0 + y, Rgb{px[0], px[1], px[2]}, px[3] * 235 / 255);
        }
}

Rgb colorFor(hy300::bootlog::LineKind kind) {
    switch (kind) {
        case hy300::bootlog::LineKind::kError: return {255, 95, 110};
        case hy300::bootlog::LineKind::kWarning: return {255, 200, 90};
        case hy300::bootlog::LineKind::kKernel: return {110, 220, 140};
        case hy300::bootlog::LineKind::kProgress: return {200, 150, 255};
        case hy300::bootlog::LineKind::kRuntime: return {120, 190, 255};
        default: return {170, 170, 185};
    }
}

void readLog(BootModel* model, std::atomic<bool>* running) {
    FILE* in = popen("logcat -b all -v brief", "r");
    if (!in) return;
    char line[1024];
    while (running->load() && fgets(line, sizeof(line), in)) model->addLine(line);
    pclose(in);
}

void drawFrame(Canvas& canvas, BootModel& model, Font& mono, Font& header, const Image& logo, int shownProgress) {
    const int W = canvas.width, H = canvas.height;
    canvas.fill(0, 0, W, H, {8, 6, 16});
    header.draw(canvas, 16, 30, "HY300 :: RK3566 :: booting", {190, 140, 255});
    char clock[96];
    snprintf(clock, sizeof(clock), "%6.2fs  %s", uptimeMillis() / 1000.0, model.stage().c_str());
    header.draw(canvas, W - 16 - header.measure(clock), 30, clock, {120, 110, 150});
    canvas.fill(0, 40, W, 41, {60, 40, 110});

    const int top = 48, bottom = H - 40, lh = std::max(mono.lineHeight(), 1);
    const auto lines = model.lastLines((bottom - top) / lh);
    int y = top + lh;
    for (const auto& l : lines) {
        mono.draw(canvas, 12, y, l.text, colorFor(l.kind), 190);
        y += lh;
    }

    drawLogo(canvas, logo, W - kLogoSize - 16, H - kLogoSize - 52, kLogoSize);
    canvas.fill(16, H - 26, W - 16, H - 16, {35, 25, 60});
    canvas.fill(16, H - 26, 16 + (W - 32) * shownProgress / 100, H - 16, {160, 90, 255});
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr, "uso: %s <largura> <altura> <logo.png> [--test]\n", argv[0]);
        return 2;
    }
    const int W = atoi(argv[1]), H = atoi(argv[2]);
    const bool test = argc > 4 && strcmp(argv[4], "--test") == 0;
    const int64_t deadline = uptimeMillis() + (test ? 15000 : 180000);

    sp<ProcessState> proc(ProcessState::self());
    ProcessState::self()->startThreadPool();

    sp<SurfaceComposerClient> client = new SurfaceComposerClient();
    if (client->initCheck() != NO_ERROR) return 3;
    sp<SurfaceControl> control =
            client->createSurface(String8("hy300-bootlog"), W, H, PIXEL_FORMAT_RGBX_8888, 0);
    if (control == nullptr || !control->isValid()) return 4;
    SurfaceComposerClient::Transaction().setLayer(control, 0x7ffffffe).show(control).apply();
    sp<Surface> surface = control->getSurface();
    ANativeWindow* window = surface.get();
    native_window_api_connect(window, NATIVE_WINDOW_API_CPU);

    FT_Library ft;
    if (FT_Init_FreeType(&ft) != 0) return 5;
    Font mono, header;
    if (!mono.open(ft, "/system/fonts/DroidSansMono.ttf", 13)) return 6;
    if (!header.open(ft, "/system/fonts/Roboto-Regular.ttf", 18) &&
        !header.open(ft, "/system/fonts/DroidSansMono.ttf", 18))
        return 6;
    Image logo;
    loadPng(argv[3], &logo);

    BootModel model;
    std::atomic<bool> running(true);
    std::thread reader(readLog, &model, &running);
    reader.detach();

    bool sawZero = base::GetProperty("service.bootanim.exit", "0") != "1";
    bool readySignaled = false;
    int shownProgress = 0;
    while (true) {
        const bool exitProp = base::GetProperty("service.bootanim.exit", "0") == "1";
        if (!exitProp) sawZero = true;
        if (!test && (model.screenEnabled() || (sawZero && exitProp))) break;
        if (uptimeMillis() > deadline) break;

        ANativeWindow_Buffer buffer;
        if (ANativeWindow_lock(window, &buffer, nullptr) != 0) return readySignaled ? 0 : 7;
        Canvas canvas{static_cast<uint32_t*>(buffer.bits), buffer.width, buffer.height, buffer.stride};
        shownProgress = hy300::bootlog::stepProgress(shownProgress, model.progress());
        drawFrame(canvas, model, mono, header, logo, shownProgress);
        ANativeWindow_unlockAndPost(window);

        if (!readySignaled) {
            readySignaled = true;
            close(open("/dev/.bootlog_ready", O_CREAT | O_WRONLY | O_CLOEXEC, 0644));
        }
        usleep(kFrameMs * 1000);
    }
    running = false;
    SurfaceComposerClient::Transaction().hide(control).apply();
    return 0;
}
