use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;

use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager, RunEvent, WindowEvent,
};
use tauri_plugin_shell::ShellExt;

struct AppState {
    minimize_to_tray: AtomicBool,
    background_on_close: AtomicBool,
    backend_spawned: AtomicBool,
}

fn backend_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("ALLSAFE_BACKEND_DIR") {
        return PathBuf::from(dir);
    }
    let cwd = std::env::current_dir().unwrap_or_default();
    if cwd.join("backend").join("main.py").exists() {
        return cwd.join("backend");
    }
    if cwd.parent().map(|p| p.join("backend").join("main.py").exists()) == Some(true) {
        return cwd.parent().unwrap().join("backend");
    }
    cwd.join("backend")
}

fn read_minimize_to_tray() -> bool {
    let settings_path = backend_dir().join("data").join("settings.json");
    let Ok(text) = fs::read_to_string(settings_path) else {
        return true;
    };
    let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) else {
        return true;
    };
    json.get("system")
        .and_then(|s| s.get("minimize_to_tray"))
        .and_then(|v| v.as_bool())
        .unwrap_or(true)
}

fn spawn_backend(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<AppState>();
    if state.backend_spawned.swap(true, Ordering::SeqCst) {
        return Ok(());
    }

    let shell = app.shell();
    if let Ok(sidecar) = shell.sidecar("allsafe-api") {
        sidecar
            .spawn()
            .map_err(|e| format!("sidecar spawn failed: {e}"))?;
        log::info!("AllSafe API sidecar started");
        return Ok(());
    }

    let backend = backend_dir();
    let main_py = backend.join("main.py");
    if main_py.exists() {
        shell
            .command("python")
            .args(["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"])
            .current_dir(backend)
            .spawn()
            .map_err(|e| format!("python backend spawn failed: {e}"))?;
        log::info!("AllSafe API dev backend started");
        return Ok(());
    }

    Err("Backend executable not found".to_string())
}

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

fn hide_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.hide();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let minimize_to_tray = read_minimize_to_tray();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState {
            minimize_to_tray: AtomicBool::new(minimize_to_tray),
            background_on_close: AtomicBool::new(true),
            backend_spawned: AtomicBool::new(false),
        })
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if let Err(err) = spawn_backend(app.handle()) {
                log::error!("{err}");
            }

            let show_i = MenuItem::with_id(app, "show", "Show AllSafe", true, None::<&str>)?;
            let hide_i = MenuItem::with_id(app, "hide", "Hide Window", true, None::<&str>)?;
            let restart_i =
                MenuItem::with_id(app, "restart", "Restart Monitors", true, None::<&str>)?;
            let exit_i = MenuItem::with_id(app, "exit", "Exit AllSafe", true, None::<&str>)?;
            let menu = Menu::with_items(
                app,
                &[
                    &show_i,
                    &hide_i,
                    &PredefinedMenuItem::separator(app, None)?,
                    &restart_i,
                    &PredefinedMenuItem::separator(app, None)?,
                    &exit_i,
                ],
            )?;

            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .tooltip("AllSafe Security — Protected")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => show_main_window(app),
                    "hide" => hide_main_window(app),
                    "restart" => {
                        let _ = app.emit("allsafe-restart-monitors", ());
                    }
                    "exit" => {
                        let _ = app.emit("allsafe-exit", ());
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(app)?;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let app = window.app_handle();
                let state = app.state::<AppState>();
                if state.minimize_to_tray.load(Ordering::SeqCst) {
                    api.prevent_close();
                    let _ = window.hide();
                    let _ = app.emit("allsafe-background-mode", true);
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                let _ = app.emit("allsafe-shutdown", ());
            }
        });
}
