"""Tests for gpu_thermal.py with a fake pynvml (no GPU needed).

    cd teams/08-monitoring/metrics_logger && python -m pytest test_gpu_thermal.py -q
"""
import json
import sys
import types

import pytest

import gpu_thermal
from gpu_thermal import HW_THERMAL_SLOWDOWN, SW_THERMAL_SLOWDOWN, gpu_thermal as read
from metrics_writer import MetricsWriter

POWER_CAP = 0x04               # nvmlClocksThrottleReasonSwPowerCap: not a thermal reason
GPU_IDLE = 0x01


class FakeNvml:
    """The part of pynvml that gpu_thermal uses. temps / reasons: one value per GPU index."""
    NVML_TEMPERATURE_GPU = 0

    def __init__(self, temps, reasons, fail=False, event_api=True):
        self.temps, self.reasons, self.fail = temps, reasons, fail
        self.asked = []
        if event_api:
            self.nvmlDeviceGetCurrentClocksEventReasons = lambda h: self.reasons[h]

    def nvmlDeviceGetHandleByIndex(self, i):
        if self.fail:
            raise RuntimeError("NVMLError_GpuIsLost")
        self.asked.append(i)
        return i

    def nvmlDeviceGetTemperature(self, h, sensor):
        assert sensor == self.NVML_TEMPERATURE_GPU
        return self.temps[h]

    def nvmlDeviceGetCurrentClocksThrottleReasons(self, h):   # older pynvml name
        return self.reasons[h]


def test_normal_temperature():
    assert read(0, FakeNvml([64], [GPU_IDLE])) == {"gpu_temp_c": 64.0, "gpu_thermal_throttle": 0}


@pytest.mark.parametrize("bits", [HW_THERMAL_SLOWDOWN, SW_THERMAL_SLOWDOWN, HW_THERMAL_SLOWDOWN | POWER_CAP])
def test_hot_and_thermal_throttle(bits):
    assert read(0, FakeNvml([87], [bits])) == {"gpu_temp_c": 87.0, "gpu_thermal_throttle": 1}


def test_other_throttle_reasons_do_not_count():
    # 85 C but only the power cap is slowing it: not thermal
    assert read(0, FakeNvml([85], [POWER_CAP | GPU_IDLE]))["gpu_thermal_throttle"] == 0


def test_older_pynvml_without_event_api():
    assert read(0, FakeNvml([90], [SW_THERMAL_SLOWDOWN], event_api=False))["gpu_thermal_throttle"] == 1


def test_device_defaults_to_local_rank(monkeypatch):
    nvml = FakeNvml([50, 70], [0, HW_THERMAL_SLOWDOWN])
    monkeypatch.setenv("LOCAL_RANK", "1")
    assert read(nvml=nvml) == {"gpu_temp_c": 70.0, "gpu_thermal_throttle": 1} and nvml.asked == [1]


def test_failed_read_writes_nothing():
    assert read(0, FakeNvml([70], [0], fail=True)) == {}


@pytest.fixture
def fresh(monkeypatch):
    """Forget any NVML start from an earlier test."""
    monkeypatch.setattr(gpu_thermal, "_nvml", None)


def test_cpu_only_no_pynvml(monkeypatch, fresh):
    monkeypatch.setitem(sys.modules, "pynvml", None)          # import pynvml -> ImportError
    assert read() == {}
    assert read() == {}                                       # tried once, still {}


def test_cpu_only_nvml_cannot_start(monkeypatch, fresh):
    def no_driver():
        raise RuntimeError("NVMLError_LibraryNotFound")
    monkeypatch.setitem(sys.modules, "pynvml", types.SimpleNamespace(nvmlInit=no_driver))
    assert read() == {}


def test_real_module_path(monkeypatch, fresh):
    fake = FakeNvml([76], [0])
    started = []
    fake.nvmlInit = lambda: started.append(1)
    monkeypatch.setitem(sys.modules, "pynvml", fake)
    monkeypatch.delenv("LOCAL_RANK", raising=False)
    assert read() == {"gpu_temp_c": 76.0, "gpu_thermal_throttle": 0}
    read()
    assert started == [1]                                     # nvmlInit once per process


def test_writer_stores_both_and_maps_temp_c(tmp_path):
    path = tmp_path / "metrics.jsonl"
    with MetricsWriter(str(path), flush_every=1) as w:
        w.write(1, loss_ntp=2.0, **read(0, FakeNvml([88], [HW_THERMAL_SLOWDOWN])))
        w.write(2, loss_ntp=2.0, temp_c=70.5)                 # G6's name
        w.write(3, loss_ntp=2.0, **{})                        # CPU-only: nothing extra
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["gpu_temp_c"] == 88.0 and rows[0]["gpu_thermal_throttle"] == 1
    assert rows[1]["gpu_temp_c"] == 70.5 and "temp_c" not in rows[1]
    assert "gpu_temp_c" not in rows[2]
