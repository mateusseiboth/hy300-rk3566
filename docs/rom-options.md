# Opções de ROM

Pesquisa (nov/2026): **não existe ROM custom nem port Linux pronto para o HY300 RK3566.**
Os projetos públicos de HY300 são para Allwinner H713 (ex.: `shift/sun50iw12p1-research`).

Decisão atual: **ficar no Android** (melhor ecossistema de apps); Linux fica para depois.

## GSI (Android mais novo)

- Treble ok, VNDK 32, partições dinâmicas → GSI é possível.
- Vendor é **32 bits** → precisa de GSI `arm32_binder64` (a64), mais raro, especialmente ATV.
- Perdas a portar: keystone (ganchos no `services.jar`), autofoco (`libfocusvahysd.so` em
  `/system`), app HDMI-in, app de configuração.
- Recuperação: backup completo + modo **MaskROM** do Rockchip (`rkdeveloptool`/RKDevTool).

## Linux mainline (futuro)

- RK3566 tem bom suporte mainline (panfrost, etc.).
- A portar: DTS a partir do DTB original (painel LVDS, regulators, motor de foco, IR),
  Wi-Fi AIC8800 (driver fora da árvore), keystone no compositor.
- **RK628 HDMI-in não tem driver mainline.**
- Testar primeiro por SD/USB, sem tocar no eMMC.

## Descartado

- ChromeOS Flex: só x86.
- Firefox OS / B2G: projeto morto.
