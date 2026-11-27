"""What machine Drakter runs on, and whether it changed since it last looked.

Nothing here is configured by hand: every value is read from the running system at startup
and again every `REFRESH_S`, so moving the install (or its disk) to another computer, or
adding RAM or a GPU, is noticed without anyone telling Drakter.

- `probe()` reads the static profile (no root needed). Linux reads DMI, /proc and `lspci`;
  other systems fall back to `platform`/`os`, with what they can tell.
- `live()` reads what moves (free RAM, load, battery, free disk). Cheap: no subprocess.
- `HardwareTracker` compares each probe with `<data_dir>/system/hardware.json` and records
  a change: `new_machine` (other vendor, model, board or CPU), `known_machine` (back on one
  seen before), `hardware_changed` (same machine, other RAM, GPU or threads) or `os_changed`.

The file holds no serial numbers, UUIDs or machine-id: only what `lspci` and DMI show to any
user. It lives outside the repository, with mode 600.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

from app.core.config import ensure_private_dir

logger = logging.getLogger("drakter.hardware")

REFRESH_S: Final = 600.0
MAX_CHANGES: Final = 10
MAX_MACHINES: Final = 10
_DMI: Final = Path("/sys/class/dmi/id")
_GPU_VENDORS: Final = {"0x8086": "Intel", "0x10de": "NVIDIA", "0x1002": "AMD", "0x1af4": "Virtio", "0x15ad": "VMware"}
# SMBIOS chassis types (DSP0134 7.4.1).
_LAPTOP: Final = {8, 9, 10, 14, 31, 32}
_DESKTOP: Final = {3, 4, 5, 6, 7, 15, 16, 35, 36}
_VIRTUAL_HINTS: Final = ("qemu", "kvm", "vmware", "virtualbox", "innotek", "xen", "bochs", "microsoft corporation virtual", "parallels")
_PLACEHOLDERS: Final = {"", "to be filled by o.e.m.", "default string", "system product name", "not specified", "none", "0123456789"}

ChangeKind = Literal["new_machine", "known_machine", "hardware_changed", "os_changed"]


@dataclass(frozen=True)
class Gpu:
    vendor: str
    name: str
    integrated: bool | None  # None when it cannot be told


@dataclass(frozen=True)
class HardwareProfile:
    vendor: str | None
    model: str | None
    form_factor: Literal["laptop", "desktop", "all_in_one", "tablet", "server", "virtual", "unknown"]
    cpu_model: str | None
    cpu_cores: int | None
    cpu_threads: int | None
    cpu_max_mhz: int | None
    memory_gb: float | None
    swap_gb: float | None
    gpus: tuple[Gpu, ...]
    has_battery: bool
    os_name: str
    kernel: str
    arch: str
    session: str | None  # e.g. "wayland · ubuntu:GNOME"
    hostname: str
    machine_key: str  # which computer
    hardware_key: str  # which configuration of that computer
    probed_at: str

    def label(self) -> str:
        """Short name a person would use: «Lenovo ThinkPad T490»."""
        name = " ".join(p for p in (self.vendor, self.model) if p) or self.hostname
        return name

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["gpus"] = [asdict(g) for g in self.gpus]
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HardwareProfile:
        values = dict(data)
        values["gpus"] = tuple(Gpu(**g) for g in values.get("gpus") or ())
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in values.items() if k in known})


@dataclass(frozen=True)
class LiveResources:
    memory_available_gb: float | None
    load_pct: int | None  # 1-minute load over threads, 0..100+
    battery_pct: int | None
    battery_state: Literal["charging", "discharging", "full", "not_charging", "unknown"] | None
    on_ac_power: bool | None
    disk_free_gb: float | None  # where Drakter keeps its data
    system_uptime_s: int | None


@dataclass(frozen=True)
class HardwareChange:
    kind: ChangeKind
    detected_at: str
    previous_label: str
    current_label: str
    details: tuple[str, ...]  # human lines, Spanish: «RAM: 16 GB → 32 GB»

    def to_json(self) -> dict[str, Any]:
        return {**asdict(self), "details": list(self.details)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> HardwareChange:
        return cls(
            kind=data["kind"],
            detected_at=data["detected_at"],
            previous_label=data.get("previous_label", ""),
            current_label=data.get("current_label", ""),
            details=tuple(data.get("details") or ()),
        )


@dataclass
class KnownMachine:
    machine_key: str
    label: str
    first_seen_at: str
    last_seen_at: str


# ── reading the system ──────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _dmi(name: str) -> str | None:
    value = _read(_DMI / name)
    if value is None or value.lower() in _PLACEHOLDERS:
        return None
    return value


def _vendor_name(raw: str | None) -> str | None:
    if not raw:
        return None
    pretty = {"LENOVO": "Lenovo", "HP": "HP", "Hewlett-Packard": "HP", "Dell Inc.": "Dell", "ASUSTeK COMPUTER INC.": "ASUS"}
    return pretty.get(raw, raw.title() if raw.isupper() and len(raw) > 4 else raw)


def _form_factor(vendor: str | None, product: str | None, virtual: bool) -> str:
    if virtual:
        return "virtual"
    try:
        chassis = int(_read(_DMI / "chassis_type") or "")
    except ValueError:
        chassis = None
    if chassis in _LAPTOP:
        return "laptop"
    if chassis in _DESKTOP:
        return "desktop"
    if chassis == 13:
        return "all_in_one"
    if chassis in {30}:
        return "tablet"
    if chassis in {17, 23, 28, 29}:
        return "server"
    return "unknown"


def _cpuinfo() -> tuple[str | None, int | None, int | None, bool]:
    text = _read(Path("/proc/cpuinfo"))
    if not text:
        return platform.processor() or None, None, os.cpu_count(), False
    model = None
    cores: set[tuple[str, str]] = set()
    threads = 0
    physical = core = "0"
    hypervisor = False
    for line in text.splitlines():
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key == "processor":
            threads += 1
        elif key == "model name" and model is None:
            model = value
        elif key == "physical id":
            physical = value
        elif key == "core id":
            core = value
            cores.add((physical, core))
        elif key == "flags" and " hypervisor" in f" {value}":
            hypervisor = True
    if model:
        model = re.sub(r"\((R|TM|tm)\)", "", model)
        model = re.sub(r"\s+CPU\s+@.*$", "", model)
        model = " ".join(model.split())
    return model, len(cores) or None, threads or os.cpu_count(), hypervisor


def _cpu_max_mhz() -> int | None:
    raw = _read(Path("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"))
    try:
        return round(int(raw) / 1000) if raw else None
    except ValueError:
        return None


def _meminfo() -> dict[str, int]:
    text = _read(Path("/proc/meminfo")) or ""
    values: dict[str, int] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0])  # kB
    return values


def _gb(kib: int | None) -> float | None:
    return None if kib is None else round(kib / 1024 / 1024, 1)


def _windows_memory_gb() -> tuple[float | None, float | None]:
    """Total and available RAM on Windows, without psutil."""
    try:
        import ctypes

        class _Status(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]  # fmt: skip

        status = _Status()
        status.dwLength = ctypes.sizeof(_Status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
            return None, None
        return round(status.ullTotalPhys / 1024**3, 1), round(status.ullAvailPhys / 1024**3, 1)
    except Exception:  # noqa: BLE001 - optional on a non-Linux system
        return None, None


def _gpus() -> tuple[Gpu, ...]:
    """`lspci` names the device; without it, the PCI vendor of each DRM card."""
    found: list[Gpu] = []
    lspci = shutil.which("lspci")
    if lspci:
        try:
            out = subprocess.run(  # noqa: S603 - fixed arguments, no shell
                [lspci, "-mm", "-nn"], capture_output=True, text=True, timeout=3, check=False
            ).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        for line in out.splitlines():
            fields = re.findall(r'"([^"]*)"', line)
            if len(fields) < 3 or not re.search(r"\[(0300|0302|0380)\]", fields[0]):
                continue
            vendor = re.sub(r"\s*\[[0-9a-f]{4}\]$", "", fields[1]).replace(" Corporation", "")
            vendor = {"Advanced Micro Devices, Inc. [AMD/ATI]": "AMD", "NVIDIA": "NVIDIA"}.get(vendor, vendor)
            device = re.sub(r"\s*\[[0-9a-f]{4}\]$", "", fields[2])
            bracket = re.search(r"\[([^\]]+)\]", device)  # «WhiskeyLake-U GT2 [UHD Graphics 620]»
            name = bracket.group(1) if bracket else device
            found.append(Gpu(vendor=vendor, name=name, integrated=_integrated(vendor, fields[0])))
    if found:
        return tuple(found)
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]")):
        vendor_id = _read(card / "device" / "vendor")
        if vendor_id:
            vendor = _GPU_VENDORS.get(vendor_id, vendor_id)
            found.append(Gpu(vendor=vendor, name=f"GPU {vendor}", integrated=_integrated(vendor, "")))
    return tuple(found)


def _integrated(vendor: str, pci_class: str) -> bool | None:
    if vendor.startswith("Intel"):
        return "[0380]" not in pci_class  # Intel Arc shows as 0300 too; good enough for a hint
    if vendor.startswith("NVIDIA"):
        return False
    return None


def _os_name() -> str:
    text = _read(Path("/etc/os-release"))
    if text:
        match = re.search(r'^PRETTY_NAME="?([^"\n]+)"?', text, re.MULTILINE)
        if match:
            return match.group(1)
    if platform.system() == "Windows":
        return f"Windows {platform.release()}"
    return f"{platform.system()} {platform.release()}".strip()


def _session() -> str | None:
    parts = [os.environ.get("XDG_SESSION_TYPE"), os.environ.get("XDG_CURRENT_DESKTOP")]
    joined = " · ".join(p for p in parts if p)
    return joined or None


def _has_battery() -> bool:
    return any(Path("/sys/class/power_supply").glob("BAT*"))


def _key(*parts: object) -> str:
    material = "\x00".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _fallback_identity() -> str:
    """Without DMI (some VMs, non-Linux): the machine-id, hashed, never stored raw."""
    for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        value = _read(path)
        if value:
            return hashlib.sha256(value.encode()).hexdigest()
    return socket.gethostname()


def probe() -> HardwareProfile:
    raw_vendor, product = _dmi("sys_vendor"), _dmi("product_name")
    version, board = _dmi("product_version"), _dmi("board_name")
    vendor = _vendor_name(raw_vendor)
    # Lenovo keeps the commercial name in product_version («ThinkPad T490»); others in product_name.
    model = version if version and not re.fullmatch(r"[\d.]+|None", version) and raw_vendor == "LENOVO" else product
    cpu_model, cores, threads, hypervisor = _cpuinfo()
    identity = " ".join(x for x in (raw_vendor, product, board) if x).lower()
    virtual = hypervisor or any(hint in identity for hint in _VIRTUAL_HINTS)
    mem = _meminfo()
    memory_gb, swap_gb = _gb(mem.get("MemTotal")), _gb(mem.get("SwapTotal"))
    if memory_gb is None and platform.system() == "Windows":
        memory_gb, _ = _windows_memory_gb()
    gpus = _gpus()
    machine_key = _key(raw_vendor, product, board, cpu_model) if (raw_vendor or product) else _key(_fallback_identity(), cpu_model)
    # RAM rounded to the GB: the kernel reserves a little more or less between boots.
    hardware_key = _key(machine_key, round(memory_gb or 0), threads, *(f"{g.vendor}:{g.name}" for g in gpus))
    return HardwareProfile(
        vendor=vendor,
        model=model,
        form_factor=_form_factor(vendor, product, virtual),  # type: ignore[arg-type]
        cpu_model=cpu_model,
        cpu_cores=cores,
        cpu_threads=threads,
        cpu_max_mhz=_cpu_max_mhz(),
        memory_gb=memory_gb,
        swap_gb=swap_gb,
        gpus=gpus,
        has_battery=_has_battery(),
        os_name=_os_name(),
        kernel=platform.release(),
        arch=platform.machine(),
        session=_session(),
        hostname=socket.gethostname(),
        machine_key=machine_key,
        hardware_key=hardware_key,
        probed_at=_now(),
    )


def live(data_dir: Path | None = None) -> LiveResources:
    mem = _meminfo()
    available = _gb(mem.get("MemAvailable"))
    if available is None and platform.system() == "Windows":
        _, available = _windows_memory_gb()
    load = None
    try:
        threads = os.cpu_count() or 1
        load = round(os.getloadavg()[0] / threads * 100)
    except (OSError, AttributeError):
        pass
    battery_pct = battery_state = None
    batteries = sorted(Path("/sys/class/power_supply").glob("BAT*"))
    if batteries:
        try:
            battery_pct = int(_read(batteries[0] / "capacity") or "")
        except ValueError:
            battery_pct = None
        status = (_read(batteries[0] / "status") or "unknown").lower().replace(" ", "_")
        battery_state = status if status in {"charging", "discharging", "full", "not_charging"} else "unknown"
    on_ac = None
    for supply in Path("/sys/class/power_supply").glob("*"):
        if (_read(supply / "type") or "") == "Mains":
            on_ac = (_read(supply / "online") or "0") == "1"
            break
    disk_free = None
    if data_dir is not None:
        try:
            disk_free = round(shutil.disk_usage(data_dir).free / 1024**3, 1)
        except OSError:
            disk_free = None
    uptime = None
    raw_uptime = _read(Path("/proc/uptime"))
    if raw_uptime:
        try:
            uptime = int(float(raw_uptime.split()[0]))
        except ValueError:
            uptime = None
    return LiveResources(
        memory_available_gb=available,
        load_pct=load,
        battery_pct=battery_pct,
        battery_state=battery_state,  # type: ignore[arg-type]
        on_ac_power=on_ac,
        disk_free_gb=disk_free,
        system_uptime_s=uptime,
    )


# ── comparing with what it knew ─────────────────────────────────────────────


def _gpu_list(profile: HardwareProfile) -> str:
    return ", ".join(f"{g.vendor} {g.name}".strip() for g in profile.gpus) or "ninguna detectada"


def describe_changes(before: HardwareProfile, after: HardwareProfile) -> tuple[str, ...]:
    lines: list[str] = []

    def diff(label: str, a: object, b: object) -> None:
        if a != b:
            lines.append(f"{label}: {a if a not in (None, '') else '?'} → {b if b not in (None, '') else '?'}")

    diff("Equipo", before.label(), after.label())
    diff("CPU", before.cpu_model, after.cpu_model)
    diff("Hilos", before.cpu_threads, after.cpu_threads)
    if round(before.memory_gb or 0) != round(after.memory_gb or 0):
        lines.append(f"RAM: {round(before.memory_gb or 0)} GB → {round(after.memory_gb or 0)} GB")
    diff("GPU", _gpu_list(before), _gpu_list(after))
    diff("Sistema", before.os_name, after.os_name)
    diff("Tipo", before.form_factor, after.form_factor)
    return tuple(lines)


class HardwareTracker:
    """Keeps the current profile and the last change. Thread-safe; `refresh` does the I/O."""

    def __init__(self, data_dir: Path, *, refresh_s: float = REFRESH_S) -> None:
        self._dir = data_dir / "system"
        self._path = self._dir / "hardware.json"
        self._data_dir = data_dir
        self._refresh_s = refresh_s
        self._lock = threading.Lock()
        self._refreshing = False
        self._checked_at = float("-inf")
        self.profile: HardwareProfile | None = None
        self.change: HardwareChange | None = None  # the latest one, kept until another comes
        self.changes: list[HardwareChange] = []
        self.machines: list[KnownMachine] = []
        self.first_seen_at: str | None = None

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        ensure_private_dir(self._dir)
        fd, tmp = tempfile.mkstemp(dir=self._dir, prefix=".hardware-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=1)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self._path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def refresh(self) -> HardwareChange | None:
        """Probe, compare with the stored profile, persist. Returns a change found now, if any."""
        current = probe()
        stored = self._load()
        previous = None
        try:
            if isinstance(stored.get("current"), dict):
                previous = HardwareProfile.from_json(stored["current"])
        except (TypeError, KeyError):
            previous = None
        changes = []
        for raw in stored.get("changes") or []:
            try:
                changes.append(HardwareChange.from_json(raw))
            except (TypeError, KeyError):
                continue
        machines = [
            KnownMachine(**m) for m in stored.get("machines") or [] if isinstance(m, dict) and "machine_key" in m
        ]
        now = current.probed_at
        found: HardwareChange | None = None
        if previous is not None:
            kind: ChangeKind | None = None
            if previous.machine_key != current.machine_key:
                known = any(m.machine_key == current.machine_key for m in machines)
                kind = "known_machine" if known else "new_machine"
            elif previous.hardware_key != current.hardware_key:
                kind = "hardware_changed"
            elif previous.os_name != current.os_name:
                kind = "os_changed"
            if kind is not None:
                found = HardwareChange(
                    kind=kind,
                    detected_at=now,
                    previous_label=previous.label(),
                    current_label=current.label(),
                    details=describe_changes(previous, current),
                )
                changes = [found, *changes][:MAX_CHANGES]
                logger.info("hardware changed", extra={"event": "hardware_changed", "kind": kind})
        entry = next((m for m in machines if m.machine_key == current.machine_key), None)
        if entry is None:
            machines.insert(0, KnownMachine(current.machine_key, current.label(), now, now))
        else:
            entry.last_seen_at, entry.label = now, current.label()
        machines = sorted(machines, key=lambda m: m.last_seen_at, reverse=True)[:MAX_MACHINES]
        first_seen = stored.get("first_seen_at") or now
        try:
            self._save(
                {
                    "version": 1,
                    "first_seen_at": first_seen,
                    "current": current.to_json(),
                    "changes": [c.to_json() for c in changes],
                    "machines": [asdict(m) for m in machines],
                }
            )
        except OSError:
            logger.warning("hardware profile not saved", extra={"event": "hardware_save_failed"})
        with self._lock:
            self.profile = current
            self.changes = changes
            self.change = changes[0] if changes else None
            self.machines = machines
            self.first_seen_at = first_seen
            self._checked_at = time.monotonic()
        return found

    def refresh_if_stale(self) -> None:
        """Non-blocking: a stale profile is re-read in a daemon thread. Safe on the event loop."""
        with self._lock:
            if self._refreshing or time.monotonic() - self._checked_at < self._refresh_s:
                return
            self._refreshing = True

        def run() -> None:
            try:
                self.refresh()
            except Exception:  # noqa: BLE001 - the old profile stays; next turn tries again
                logger.warning("hardware probe failed", extra={"event": "hardware_probe_failed"})
            finally:
                with self._lock:
                    self._refreshing = False
                    self._checked_at = max(self._checked_at, time.monotonic() - self._refresh_s + 60)

        threading.Thread(target=run, name="drakter-hardware", daemon=True).start()


# ── text for the model ──────────────────────────────────────────────────────

_FORM: Final = {
    "laptop": "portátil",
    "desktop": "sobremesa",
    "all_in_one": "todo en uno",
    "tablet": "tableta",
    "server": "servidor",
    "virtual": "máquina virtual",
    "unknown": "equipo",
}


def _num(value: float) -> str:
    return f"{value:.1f}".replace(".", ",").removesuffix(",0")


def summary_line(profile: HardwareProfile, now: LiveResources) -> str:
    """One line for the turn prompt: what it runs on and how loaded it is right now."""
    cpu = profile.cpu_model or "CPU desconocida"
    if profile.cpu_cores and profile.cpu_threads:
        cpu += f" ({profile.cpu_cores} núcleos/{profile.cpu_threads} hilos)"
    ram = f"{_num(profile.memory_gb)} GB RAM" if profile.memory_gb else "RAM desconocida"
    if now.memory_available_gb is not None:
        ram += f" ({_num(now.memory_available_gb)} libres)"
    gpu = _gpu_list(profile)
    if profile.gpus and all(g.integrated for g in profile.gpus):
        gpu += ", integrada, sin VRAM propia"
    parts = [f"{_FORM.get(profile.form_factor, 'equipo')} {profile.label()}", cpu, ram, f"GPU {gpu}", profile.os_name]
    if now.load_pct is not None:
        parts.append(f"carga {now.load_pct} %")
    if now.battery_pct is not None:
        state = {"charging": "cargando", "discharging": "con batería", "full": "llena", "not_charging": "enchufado"}
        parts.append(f"batería {now.battery_pct} % {state.get(now.battery_state or '', '')}".strip())
    return "[equipo: " + " · ".join(parts) + "]"


def change_line(change: HardwareChange) -> str:
    if change.kind == "new_machine":
        head = f"Drakter se ha movido a otro equipo: antes {change.previous_label}, ahora {change.current_label}"
    elif change.kind == "known_machine":
        head = f"Drakter vuelve a {change.current_label}, un equipo en el que ya estuvo (antes {change.previous_label})"
    elif change.kind == "hardware_changed":
        head = f"El hardware de {change.current_label} ha cambiado"
    else:
        head = f"El sistema operativo de {change.current_label} ha cambiado"
    detail = "; ".join(change.details[:5])
    return (
        f"[aviso del sistema: {head} ({detail}). Lo que supieras del equipo anterior ya no vale: "
        "usa los datos de equipo de arriba. Si viene al caso, menciónalo una vez.]"
    )


__all__ = [
    "Gpu",
    "HardwareChange",
    "HardwareProfile",
    "HardwareTracker",
    "KnownMachine",
    "LiveResources",
    "change_line",
    "describe_changes",
    "live",
    "probe",
    "summary_line",
]

