"""gpu_temp_c and gpu_thermal_throttle for one optimizer step, read from NVML. Optional: {} without a GPU.

A hot GPU slows its clocks to protect itself (thermal slowdown), so the step time grows with no change in the
code or the data. These two values let the dashboard tell that apart from a real slowdown:

    gpu_temp_c            GPU core temperature in degrees C (NVML_TEMPERATURE_GPU)
    gpu_thermal_throttle  1 when NVML's clock throttle reasons have HW thermal slowdown (0x40) or
                          SW thermal slowdown (0x20) set, else 0

    from gpu_thermal import gpu_thermal
    writer.write(step, loss_ntp=..., **gpu_thermal())

`gpu_thermal()` returns {} when pynvml is not installed, NVML cannot start (no NVIDIA driver, a CPU-only
machine), or the read fails, so the same trainer code runs on CPU and writes nothing for these names. It never
raises: a monitoring read must not stop training.

Which GPU: `device` (default: LOCAL_RANK, else 0), so each rank reads its own GPU. The writer usually runs on
rank 0 only, so per step we see rank 0's GPU; every GPU is covered by the 1-second telemetry
(`gpu_telemetry_1s`, which also accepts the name temp_c). pynvml comes from the `nvidia-ml-py` package.
"""

import os

HW_THERMAL_SLOWDOWN = 0x40     # nvmlClocksThrottleReasonHwThermalSlowdown
SW_THERMAL_SLOWDOWN = 0x20     # nvmlClocksThrottleReasonSwThermalSlowdown
THERMAL_BITS = HW_THERMAL_SLOWDOWN | SW_THERMAL_SLOWDOWN
NVML_TEMPERATURE_GPU = 0

_nvml = None                   # the pynvml module once nvmlInit() worked; False after a failed start


def _load():
    """pynvml after nvmlInit(), or None. Tried once per process."""
    global _nvml
    if _nvml is None:
        try:
            import pynvml
            pynvml.nvmlInit()
            _nvml = pynvml
        except Exception:      # noqa: BLE001 - ImportError, NVMLError (no driver), anything else: no GPU data
            _nvml = False
    return _nvml or None


def _throttle_reasons(nvml, handle) -> int:
    # newer NVML calls them "clocks event reasons"; the bits are the same
    read = getattr(nvml, "nvmlDeviceGetCurrentClocksEventReasons", None) or nvml.nvmlDeviceGetCurrentClocksThrottleReasons
    return int(read(handle))


def gpu_thermal(device=None, nvml=None) -> dict:
    """{"gpu_temp_c": float, "gpu_thermal_throttle": 0 or 1} for one GPU, or {} without NVML.

    nvml: a pynvml-like module, already started (tests pass a fake). Default: the real pynvml, started once.
    """
    nvml = nvml or _load()
    if not nvml:
        return {}
    if device is None:
        device = int(os.environ.get("LOCAL_RANK", "0"))
    try:
        handle = nvml.nvmlDeviceGetHandleByIndex(device)
        temp = float(nvml.nvmlDeviceGetTemperature(handle, getattr(nvml, "NVML_TEMPERATURE_GPU", NVML_TEMPERATURE_GPU)))
        reasons = _throttle_reasons(nvml, handle)
    except Exception:          # noqa: BLE001 - a failed read writes nothing this step
        return {}
    return {"gpu_temp_c": temp, "gpu_thermal_throttle": int(bool(reasons & THERMAL_BITS))}
