import os
import subprocess
import platform
import sys

def run(cmd, cwd=None):
    shell = platform.system() == "Windows"
    try:
        subprocess.check_call(cmd, shell=shell, cwd=cwd)
    except Exception as e:
        print(f"Error executing {cmd}: {e}")

def ignite():
    app_name = "ghoster_app"
    
    # 1. Scaffolding
    os.makedirs(f"{app_name}/src", exist_ok=True)
    os.makedirs(f"{app_name}/src-tauri/src", exist_ok=True)

    files = {
        f"{app_name}/src-tauri/Cargo.toml": """
[package]
name = "ghoster"
version = "0.1.0"
edition = "2021"
[build-dependencies]
tauri-build = { version = "1.5" }
[dependencies]
tauri = { version = "1.5", features = ["shell-open"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
ssh2 = "0.9"
tokio = { version = "1", features = ["full"] }
""",
        f"{app_name}/src-tauri/tauri.conf.json": """
{
  "build": { "distDir": "../build", "devPath": "http://localhost:3000", "beforeDevCommand": "npm start", "beforeBuildCommand": "npm run build" },
  "package": { "productName": "Ghoster" },
  "tauri": {
    "bundle": { "active": true, "identifier": "com.ghoster.io", "targets": ["all"] },
    "window": { "title": "GHOSTER", "width": 1200, "height": 800, "fullscreen": false }
  }
}
""",
        f"{app_name}/src-tauri/src/main.rs": """
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use tauri::{command, Window};
use ssh2::Session;
use std::net::TcpStream;

#[command]
async fn ghost_connect(ip: String, user: String, pass: String) -> Result<String, String> {
    let tcp = TcpStream::connect(format!("{}:22", ip)).map_err(|e| e.to_string())?;
    let mut sess = Session::new().unwrap();
    sess.set_tcp_stream(tcp);
    sess.handshake().map_err(|e| e.to_string())?;
    sess.userauth_password(&user, &pass).map_err(|e| e.to_string())?;
    let mut channel = sess.channel_session().unwrap();
    channel.request_pty("xterm", None, None).unwrap();
    channel.shell().unwrap();
    Ok("Connected".into())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![ghost_connect])
        .run(tauri::generate_context!())
        .expect("error");
}
""",
        f"{app_name}/src/App.js": """
import React, { useState } from 'react';
import { invoke } from '@tauri-apps/api/tauri';
import { Terminal } from 'xterm';
import 'xterm/css/xterm.css';

export default function App() {
  const [devs, setDevs] = useState(JSON.parse(localStorage.getItem('ghost_db') || '[]'));
  const [active, setActive] = useState(false);

  const addDevice = () => {
    const d = { id: Date.now(), name: prompt("Name"), ip: prompt("IP"), user: prompt("User"), pass: prompt("Pass") };
    const newList = [...devs, d];
    setDevs(newList);
    localStorage.setItem('ghost_db', JSON.stringify(newList));
  };

  const connect = async (d) => {
    setActive(true);
    setTimeout(async () => {
      const term = new Terminal({ theme: { background: '#000' } });
      term.open(document.getElementById('terminal'));
      await invoke('ghost_connect', { ip: d.ip, user: d.user, pass: d.pass });
    }, 100);
  };

  return (
    <div style={{ background: '#000', color: '#fff', height: '100vh', padding: '20px' }}>
      {!active ? (
        <div>
          <h1>GHOSTER DASHBOARD</h1>
          <button onClick={addDevice}>+ ADD DEVICE</button>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginTop: '20px' }}>
            {devs.map(dev => (
              <div key={dev.id} onClick={() => connect(dev)} style={{ border: '1px solid #444', padding: '15px', cursor: 'pointer' }}>
                <h3>{dev.name}</h3><p>{dev.ip}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div id="terminal" style={{ width: '100vw', height: '100vh' }}></div>
      )}
    </div>
  );
}
""",
        f"{app_name}/package.json": """
{
  "name": "ghoster",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "xterm": "^5.3.0",
    "@tauri-apps/api": "^1.5.0",
    "@tauri-apps/cli": "^1.5.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "tauri": "tauri dev"
  },
  "browserslist": { "production": [">0.2%", "not dead", "not op_mini all"], "development": ["last 1 chrome version"] }
}
"""
    }

    for path, content in files.items():
        with open(path, "w") as f:
            f.write(content.strip())

    print("--- 1. INSTALLING SYSTEM LIBRARIES (LINUX) ---")
    if platform.system() == "Linux":
        print("Note: You might be prompted for your sudo password to install build-essential and libssl-dev.")
        run(["sudo", "apt-get", "update"])
        run(["sudo", "apt-get", "install", "-y", "build-essential", "curl", "wget", "libssl-dev", "libgtk-3-dev", "libayatana-appindicator3-dev", "librsvg2-dev"])

    print("--- 2. INSTALLING NODE PACKAGES ---")
    run(["npm", "install"], cwd=app_name)

    print("--- 3. IGNITING GHOSTER ---")
    run(["npm", "run", "tauri"], cwd=app_name)

if __name__ == "__main__":
    ignite()
