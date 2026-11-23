"""O app de configurações do HY300 complementa o TvSettings; nunca o substitui.

Se algum componente habilitado declarar uma ação android.settings.*, o launcher mostra o seletor
"Concluir a ação usando" entre o TvSettings e este app.
"""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "android" / "hy300-settings"
MANIFEST = APP / "app" / "src" / "main" / "AndroidManifest.xml"
ANDROID = "{http://schemas.android.com/apk/res/android}"
COMPONENT_TAGS = ("activity", "activity-alias", "service", "receiver")


def is_enabled(component):
    return component.get(f"{ANDROID}enabled", "true") != "false"


def find_actions(component):
    return [
        action.get(f"{ANDROID}name")
        for intent_filter in component.findall("intent-filter")
        for action in intent_filter.findall("action")
    ]


def find_enabled_settings_handlers(manifest_path):
    application = ET.parse(manifest_path).getroot().find("application")
    return [
        (component.get(f"{ANDROID}name"), action)
        for tag in COMPONENT_TAGS
        for component in application.findall(tag)
        if is_enabled(component)
        for action in find_actions(component)
        if action.startswith("android.settings.")
    ]


class ManifestTest(unittest.TestCase):
    def test_no_enabled_component_handles_android_settings(self):
        self.assertEqual(find_enabled_settings_handlers(MANIFEST), [])

    def test_android_settings_activity_still_declared(self):
        application = ET.parse(MANIFEST).getroot().find("application")
        names = [a.get(f"{ANDROID}name") for a in application.findall("activity")]
        self.assertIn(".AndroidSettingsActivity", names)

    def test_tvsettings_sound_entry_kept(self):
        application = ET.parse(MANIFEST).getroot().find("application")
        main = next(a for a in application.findall("activity")
                    if a.get(f"{ANDROID}name") == ".MainActivity")
        self.assertTrue(is_enabled(main))
        self.assertIn("com.android.tv.settings.SOUND", find_actions(main))

    def test_factory_script_enables_android_settings_activity(self):
        script = (APP / "system" / "disable-txcz-settings.sh").read_text()
        self.assertIn("pm enable io.github.hy300.settings/.AndroidSettingsActivity", script)


    def test_focus_motor_permission_is_signature_and_requested(self):
        # O nó do motor é system:vendor_hy300_motor 0660 no LineageOS; o gid vem desta permissão
        # (product/etc/permissions/hy300-focus-motor.xml na árvore do aparelho).
        root = ET.parse(MANIFEST).getroot()
        name = "io.github.hy300.settings.permission.FOCUS_MOTOR"
        declared = {p.get(f"{ANDROID}name"): p.get(f"{ANDROID}protectionLevel")
                    for p in root.findall("permission")}
        self.assertEqual(declared.get(name), "signature")
        used = [p.get(f"{ANDROID}name") for p in root.findall("uses-permission")]
        self.assertIn(name, used)


if __name__ == "__main__":
    unittest.main()
