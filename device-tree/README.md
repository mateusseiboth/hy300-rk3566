# Device tree — HY300 RK3566 (TXCZ `rk3566_y356tx`)

Base para futuros ports (kernel próprio, LineageOS, Linux mainline).

| Arquivo | Origem |
|---|---|
| `rk3566-hy300-txcz.dtb` | `rk-kernel.dtb` extraído do `resource.img` (seção `second` do `boot.img`) |
| `rk3566-hy300-txcz.dts` | descompilado do `.dtb` acima (biblioteca Python `fdt`; phandles numéricos) |
| `dtbo/overlay0.dtbo/.dts` | única entrada da partição `dtbo` (bootargs + reboot modes) |
| `rk3566-hy300-txcz-live.dts` | DT **vivo** (`/sys/firmware/fdt`), após fixups do U-Boot — serial e MAC **sanitizados** |
| `board-nodes.dts` | só os nós específicos da placa (painel, motor, sensores, LEDs, IR, RK628, Wi-Fi, áudio) |

- `compatible = "rockchip,rk3566-box-demo-v10", "rockchip,rk3566"` — a TXCZ partiu da
  placa de referência *RK3566 BOX DEMO V10* do SDK Rockchip (kernel 4.19).
- Kernel: `Linux 4.19.232 #1107 SMP PREEMPT Thu Jan 18 18:07:36 CST 2024`.

Extrair do seu aparelho:

```bash
tools/rk_resource.py boot-extract ~/hy300-backup/boot.img resource.img
tools/rk_resource.py unpack resource.img res/      # res/rk-kernel.dtb
```

Painel: **1024×600** LVDS (o Android renderiza 1280×720 e o HWC reduz). Config do kernel,
módulos e dmesg em [`../kernel/`](../kernel/).
