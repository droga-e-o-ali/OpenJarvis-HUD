"""A pequena ponte local do HUD. Pode ser substituída por uma API do app futuramente."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, subprocess, threading, time

import psutil

ROOT = Path(__file__).parent


def gpu_percent():
    """O Gerenciador de Tarefas representa a GPU pelo motor mais ocupado, não pela soma deles."""
    command = """
    $engines = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction SilentlyContinue
    if ($engines) {
        $engines | Measure-Object UtilizationPercentage -Maximum | ForEach-Object { [math]::Round($_.Maximum) }
    }
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=3, check=True,
        )
        return min(100, max(0, round(float(result.stdout.strip().replace(",", ".")))))
    except Exception:
        return None


class SystemMonitor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values = {"cpu": 0, "gpu": None, "ram": 0}
        psutil.cpu_percent(None)  # inicia a janela de amostragem real do Windows
        threading.Thread(target=self._sample, daemon=True, name="atlas-monitor").start()

    def _sample(self) -> None:
        next_gpu = 0.0
        while True:
            values = {
                "cpu": round(psutil.cpu_percent(interval=1)),
                "ram": round(psutil.virtual_memory().percent),
                "gpu": self._values["gpu"],
            }
            if time.monotonic() >= next_gpu:
                values["gpu"] = gpu_percent()
                next_gpu = time.monotonic() + 2
            with self._lock:
                self._values = values

    def values(self):
        with self._lock:
            return self._values.copy()


MONITOR = SystemMonitor()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
    def do_GET(self):
        if self.path == '/api/system':
            data=json.dumps(MONITOR.values()).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
        return super().do_GET()
    def log_message(self,*args): pass
ThreadingHTTPServer(('127.0.0.1',8787),Handler).serve_forever()
