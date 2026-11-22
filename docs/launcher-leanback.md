# Launcher e recurso `android.software.leanback`

## Problema
A ROM declara `android.hardware.type.television`, mas **não** `android.software.leanback`.
A Play Store trata o aparelho como não-TV e marca apps de Android TV (ex.: Projectivy
Launcher) como "aparelho não compatível".

## Patch
`android/permissions/android.software.leanback.xml` copiado para `/system/etc/permissions/`
via overlayfs do `adb remount` (build userdebug). Script: `scripts/apply-leanback.sh`.
Reverter: `scripts/revert-leanback.sh` (+ `adb enable-verity` para reativar dm-verity).

O overlay fica em `/mnt/scratch/overlay/…` — a imagem original da `super` não é alterada.

> Não usar `android.software.leanback_only`: faz a Play esconder todos os apps de celular.

## Efeito colateral: Play Store de celular
A Play Store instalada (em `/data/app`, variante de celular) recusa rodar com `leanback`
declarado ("desinstale as atualizações da Google Play Store"). Alternativas:

- **Aurora Store** (adotado): instala/atualiza apps da Play sem o app da Play.
- Instalar a variante **Android TV** da Play Store (`com.android.vending` build TV).

## Launcher
Projectivy Launcher (`com.spocky.projengmenu`) instalado pela Aurora (recebe updates) e
definido como padrão:

```
adb shell cmd package set-home-activity com.spocky.projengmenu/.ui.home.MainActivity
```

A build do XDA é assinada pelo desenvolvedor (CN=Despesse Mickael), mas pode ter chave
diferente da build da Play (Play App Signing) — preferir a da Aurora para receber updates.

FLauncher e Microsoft Launcher removidos. Launcher original da TXCZ mantido como fallback.
