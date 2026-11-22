# Splash do U-Boot (logo de boot)

O logo exibido pelo U-Boot fica no `resource.img` (formato RSCE da Rockchip), que nesta ROM
está embutido como seção **`second`** do `boot.img` (header v2, page 2048).

Conteúdo do `resource.img` original:

| Entrada | Observação |
|---|---|
| `rk-kernel.dtb` | **device tree do kernel** (ver `device-tree/`) |
| `logo.bmp` | 1280×720, 24 bits, top-down (altura negativa), 2 bytes de padding no fim |
| `battery_*.bmp` | ícones de carga (não usados) |

Não há `logo_kernel.bmp` → depois do U-Boot a tela fica com o mesmo logo até o SurfaceFlinger
iniciar a animação de boot.

## Trocar o logo

```bash
# 1. gerar BMP 1280x720 a partir de qualquer imagem (centralizada, fundo preto)
tools/make_splash.py minha_imagem.png logo.bmp --scale 0.85 --bg 000000
# 2. injetar no boot.img extraído do SEU aparelho (scripts/backup-partitions.sh)
tools/make_splash.py inject ~/hy300-backup/boot.img logo.bmp boot_novo.img
# 3. gravar
adb root && adb push boot_novo.img /data/local/tmp/
adb shell 'dd if=/data/local/tmp/boot_novo.img of=/dev/block/by-name/boot bs=4M && sync'
```

O `inject` substitui **somente os bytes do logo, no mesmo offset** (tamanho idêntico), não
mexe em kernel/ramdisk/DTB e recalcula o SHA-1 (`id`) do header — antes ele confere que o
cálculo reproduz o `id` original, e aborta se não.

**Reverter:** gravar o `boot.img` do backup na partição `boot`.

Ferramentas: `tools/rk_resource.py` (listar/extrair/reempacotar RSCE) e `tools/make_splash.py`.
