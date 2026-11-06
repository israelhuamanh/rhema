#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::json;
use std::net::{IpAddr, Ipv4Addr, SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, PhysicalPosition, RunEvent, WebviewUrl, WebviewWindowBuilder, WindowEvent};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

struct EngineProcessState(Mutex<Option<Child>>);

fn is_engine_already_running() -> bool {
    let addr = SocketAddr::new(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)), 8765);
    TcpStream::connect_timeout(&addr, Duration::from_millis(250)).is_ok()
}

fn find_engine_executable(app: &tauri::AppHandle) -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    // 1. Ruta dentro del instalador en producción (resource_dir/rhema-engine/rhema-engine.exe)
    if let Ok(res_dir) = app.path().resource_dir() {
        candidates.push(res_dir.join("rhema-engine").join("rhema-engine.exe"));
        candidates.push(res_dir.join("rhema-engine.exe"));
    }

    // 2. Ruta junto al ejecutable principal instalado
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            candidates.push(exe_dir.join("rhema-engine").join("rhema-engine.exe"));
            candidates.push(exe_dir.join("resources").join("rhema-engine").join("rhema-engine.exe"));
            // 3. Ruta en entorno de desarrollo del monorepo
            candidates.push(
                exe_dir
                    .join("..")
                    .join("..")
                    .join("..")
                    .join("..")
                    .join("rhema-engine")
                    .join("dist")
                    .join("rhema-engine")
                    .join("rhema-engine.exe"),
            );
        }
    }

    for candidate in candidates {
        if candidate.exists() {
            return Some(candidate);
        }
    }
    None
}

fn spawn_engine_if_needed(app: &tauri::AppHandle) -> Option<Child> {
    if is_engine_already_running() {
        return None;
    }

    if let Some(engine_exe) = find_engine_executable(app) {
        let engine_dir = engine_exe
            .parent()
            .map(|p| p.to_path_buf())
            .unwrap_or_else(|| PathBuf::from("."));

        let mut cmd = Command::new(&engine_exe);
        cmd.current_dir(&engine_dir);

        #[cfg(target_os = "windows")]
        {
            const CREATE_NO_WINDOW: u32 = 0x08000000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        if let Ok(child) = cmd.spawn() {
            return Some(child);
        }
    }
    None
}

fn stop_engine_process(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<EngineProcessState>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

fn position_projector_on_secondary_if_present(app: &tauri::AppHandle, win: &tauri::WebviewWindow) {
    if let Ok(monitors) = app.available_monitors() {
        if monitors.len() >= 2 {
            let secondary = &monitors[1];
            let pos = secondary.position();
            let _ = win.set_position(PhysicalPosition::new(pos.x, pos.y));
            let _ = win.set_fullscreen(true);
        }
    }
}

#[tauri::command]
fn open_projector_window(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if let Some(win) = app.get_webview_window("projector") {
        let _ = win.show();
        let _ = win.unminimize();
        let _ = win.set_focus();
        let is_fs = win.is_fullscreen().unwrap_or(false);
        return Ok(json!({ "isOpen": true, "isFullscreen": is_fs }));
    }

    let win = WebviewWindowBuilder::new(
        &app,
        "projector",
        WebviewUrl::App("index.html?window=projector".into()),
    )
    .title("Rhema Live - Proyector")
    .inner_size(800.0, 450.0)
    .position(60.0, 60.0)
    .resizable(true)
    .decorations(false)
    .always_on_top(true)
    .visible(true)
    .build()
    .map_err(|e| e.to_string())?;

    position_projector_on_secondary_if_present(&app, &win);
    let _ = win.show();
    let _ = win.set_focus();
    let is_fs = win.is_fullscreen().unwrap_or(false);

    Ok(json!({ "isOpen": true, "isFullscreen": is_fs }))
}

#[tauri::command]
fn hide_projector_window(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if let Some(win) = app.get_webview_window("projector") {
        let _ = win.hide();
    }
    Ok(json!({ "isOpen": false, "isFullscreen": false }))
}

#[tauri::command]
fn toggle_projector_fullscreen(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if let Some(win) = app.get_webview_window("projector") {
        let _ = win.show();
        let _ = win.unminimize();
        let current_fs = win.is_fullscreen().unwrap_or(false);
        let next_fs = !current_fs;
        let _ = win.set_fullscreen(next_fs);
        let _ = win.set_focus();
        return Ok(json!({ "isOpen": true, "isFullscreen": next_fs }));
    }
    open_projector_window(app)
}

#[tauri::command]
fn get_projector_status(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if let Some(win) = app.get_webview_window("projector") {
        let is_open = win.is_visible().unwrap_or(false);
        let is_fs = win.is_fullscreen().unwrap_or(false);
        return Ok(json!({ "isOpen": is_open, "isFullscreen": is_fs }));
    }
    Ok(json!({ "isOpen": false, "isFullscreen": false }))
}

fn main() {
    let app = tauri::Builder::default()
        .manage(EngineProcessState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            open_projector_window,
            hide_projector_window,
            toggle_projector_fullscreen,
            get_projector_status
        ])
        .setup(|app| {
            // 1. Iniciar automáticamente el motor embebido rhema-engine.exe si no está corriendo
            if let Some(child) = spawn_engine_if_needed(app.handle()) {
                if let Some(state) = app.try_state::<EngineProcessState>() {
                    if let Ok(mut guard) = state.0.lock() {
                        *guard = Some(child);
                    }
                }
            }

            // 2. Mostrar ventanas nativas
            if let Some(main_win) = app.get_webview_window("main") {
                let _ = main_win.show();
                let _ = main_win.unminimize();
                let _ = main_win.set_focus();
            }

            if let Some(projector_win) = app.get_webview_window("projector") {
                let _ = projector_win.show();
                let _ = projector_win.unminimize();
                position_projector_on_secondary_if_present(app.handle(), &projector_win);
            }
            Ok(())
        })
        .on_window_event(|window, event| match event {
            WindowEvent::CloseRequested { api, .. } => {
                if window.label() == "projector" {
                    api.prevent_close();
                    let _ = window.hide();
                } else if window.label() == "main" {
                    stop_engine_process(window.app_handle());
                    window.app_handle().exit(0);
                }
            }
            _ => {}
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if let RunEvent::Exit = event {
            stop_engine_process(app_handle);
        }
    });
}
