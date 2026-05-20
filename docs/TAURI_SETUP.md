# AllSafe — Tauri desktop setup (Phase 1)

AllSafe runs as a **Tauri 2** desktop app on Windows 10/11. The React + Vite frontend is unchanged; Tauri wraps it in a native window (no Electron).

## Prerequisites (Windows)

Install these once on your development machine:

| Tool | Purpose | Install |
|------|---------|---------|
| **Node.js** 18+ | Frontend + Tauri CLI | [nodejs.org](https://nodejs.org/) |
| **Rust** (stable) | Tauri backend | [rustup.rs](https://rustup.rs/) — choose *Visual Studio C++ Build Tools* when prompted on Windows |
| **WebView2** | Runtime (usually preinstalled on Win11) | [Microsoft WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) |

After Rust is installed, open a **new** terminal and verify:

```powershell
rustc --version
cargo --version
node --version
npm --version
```

Optional: NSIS is bundled by Tauri for `.exe` installers; WiX may be used for `.msi` if selected.

## Project layout (after Phase 1)

```
ALL-Safe/
├── index.html                 # Vite entry HTML
├── package.json               # npm scripts + dependencies
├── vite.config.ts             # Vite + Tauri dev server settings
├── src/                       # React UI (unchanged)
├── dist/                      # Vite production build (generated)
├── docs/
│   └── TAURI_SETUP.md         # This file
└── src-tauri/                 # Rust / Tauri backend
    ├── Cargo.toml
    ├── tauri.conf.json        # App name, window, bundle
    ├── tauri.windows.conf.json
    ├── build.rs
    ├── capabilities/
    │   └── default.json
    ├── icons/                 # App icons (replace via `tauri icon`)
    │   └── README.md
    └── src/
        ├── main.rs            # Desktop entry
        └── lib.rs             # Tauri builder
```

## Dependencies added

**npm (dev):**

- `@tauri-apps/cli` — CLI (`tauri dev`, `tauri build`)
- `@tauri-apps/api` — Optional JS APIs for native features (future phases)

**Rust (`src-tauri/Cargo.toml`):**

- `tauri` 2.x
- `tauri-build`, `tauri-plugin-log`, `serde`, `serde_json`, `log`

No Electron packages are used.

## Configuration summary

| Setting | Value |
|---------|--------|
| App name (`productName`) | AllSafe |
| Window title | AllSafe Security |
| Bundle ID | `com.allsafe.security` |
| Theme | Dark (`theme: "Dark"`, background `#09090b`) |
| Default size | 1280 × 800 |
| Minimum size | 1024 × 640 |
| Resizable | Yes |
| Dev server | `http://localhost:5173` |
| Production assets | `dist/` |

## Install project dependencies

From the project root:

```powershell
cd F:\ALL-Safe
npm install
```

## Development mode (hot reload)

Tauri starts the Vite dev server, then opens a native window that loads it. React HMR works as in the browser.

```powershell
npm run tauri:dev
```

Equivalent:

```powershell
npx tauri dev
```

**Web-only** (no desktop shell):

```powershell
npm run dev
```

## Production build (Windows installer)

Build the React app, compile Rust, and produce installers under `src-tauri/target/release/bundle/`:

```powershell
npm run tauri:build
```

On Windows you typically get:

| Artifact | Path (under `src-tauri/target/release/bundle/`) |
|----------|--------------------------------------------------|
| **NSIS setup (.exe)** | `nsis/AllSafe_0.1.0_x64-setup.exe` (name may vary) |
| **MSI** | `msi/AllSafe_0.1.0_x64_en-US.msi` |
| **Portable binary** | `../release/allsafe.exe` (crate binary name) |

Distribute the **NSIS `*-setup.exe`** for a standard Windows installer experience.

## Custom application icon

1. Add a **1024×1024** PNG (e.g. `app-icon.png` at project root).
2. Run:

```powershell
npx tauri icon .\app-icon.png
```

3. Rebuild: `npm run tauri:build`

See `src-tauri/icons/README.md`.

## npm scripts reference

| Script | Command |
|--------|---------|
| `npm run dev` | Vite only |
| `npm run build` | Vite production build → `dist/` |
| `npm run tauri:dev` | Desktop dev + hot reload |
| `npm run tauri:build` | Windows desktop + installers |
| `npm run tauri` | Pass-through to Tauri CLI |

## Troubleshooting

- **`rustc` not found** — Install Rust via rustup and restart the terminal.
- **Port 5173 in use** — Stop other Vite instances or change `port` in `vite.config.ts` and `devUrl` in `src-tauri/tauri.conf.json` together.
- **WebView2 missing** — Install the WebView2 runtime (common on Windows 11).
- **Linker / MSVC errors** — Install *Desktop development with C++* in Visual Studio Build Tools.

## Next phases

Use `@tauri-apps/api` and Tauri plugins from Rust/JS for filesystem, notifications, system tray, etc., without changing the existing UI layout.
