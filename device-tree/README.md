# Device tree — HY300 RK3566 (TXCZ `rk3566_y356tx`)

Base para futuros ports (kernel próprio, LineageOS, Linux mainline).

| Arquivo | Origem |
|---|---|
| `rk3566-hy300-txcz.dtb` | `rk-kernel.dtb` extraído do `resource.img` (seção `second` do `boot.img`) |
| `rk3566-hy300-txcz.dts` | descompilado do `.dtb` acima (biblioteca Python `fdt`; phandles numéricos) |
| `dtbo/overlay0.dtbo/.dts` | única entrada da partição `dtbo` (bootargs + reboot modes) |

- `compatible = "rockchip,rk3566-box-demo-v10", "rockchip,rk3566"` — a TXCZ partiu da
  placa de referência *RK3566 BOX DEMO V10* do SDK Rockchip (kernel 4.19).
- Kernel: `Linux 4.19.232 #1107 SMP PREEMPT Thu Jan 18 18:07:36 CST 2024`.

Extrair do seu aparelho:

```bash
tools/rk_resource.py boot-extract ~/hy300-backup/boot.img resource.img
tools/rk_resource.py unpack resource.img res/      # res/rk-kernel.dtb
```

A fazer: DT "vivo" após fixups do U-Boot (`/sys/firmware/fdt`), `/proc/config.gz`,
lista de módulos e anotação dos nós específicos da placa (painel LVDS, RK628, motor de
foco, IR, Wi-Fi AIC, ventoinha, LED do projetor).
