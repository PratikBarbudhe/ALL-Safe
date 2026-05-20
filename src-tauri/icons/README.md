# AllSafe application icons

Place a **1024×1024** PNG source image at the project root (e.g. `app-icon.png`), then regenerate all platform icons:

```bash
npx tauri icon ./app-icon.png
```

This updates `icon.ico`, `icon.icns`, and the PNG sizes referenced in `tauri.conf.json` → `bundle.icon`.

After replacing icons, rebuild the desktop app:

```bash
npm run tauri:build
```
