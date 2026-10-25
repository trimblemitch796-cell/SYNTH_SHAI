"""ELO-ECTRIC power model (software-only simulation - NOT hardware-ready).

ALL NUMBERS ARE ILLUSTRATIVE EXAMPLE VALUES, not engineering specs.

  - 2 kWh battery pack with a state of charge (SoC)
  - idle draw + energy per degree of joint motion
  - simple heat rise from energy used, and cooling toward ambient
  - a RESERVE that tasks can never use - kept for a safe stop
  - low battery -> MONITOR fault (144 HOLD)
  - over-temperature -> critical MONITOR fault (SAFE_LOCK)
"""
import math


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


# ---- EXAMPLE VALUES (illustrative only) -------------------------------
CAPACITY_WH = 2000.0        # 2 kWh pack
RESERVE_WH = 100.0          # 5 % kept back for safe stop, never for tasks
IDLE_W = 60.0               # idle draw in watts
LOW_SOC = 0.15              # below 15 % charge -> LOW_BATTERY fault (HOLD)
AMBIENT_C = 25.0
HEAT_C_PER_WH = 0.5         # pack warms 0.5 °C per Wh used
COOL_PER_S = 0.01           # 1 % of the gap to ambient lost per second
OVER_TEMP_C = 60.0          # above this -> OVER_TEMP critical fault (SAFE_LOCK)


class PowerModel:
    def __init__(self, soc=1.0, temp_c=AMBIENT_C):
        if not _finite_number(soc) or not 0.0 <= soc <= 1.0:
            raise ValueError("soc must be a number from 0 to 1")
        if not _finite_number(temp_c):
            raise ValueError("temp_c must be a finite number")
        self._energy_wh = CAPACITY_WH * soc
        self._temp_c = float(temp_c)

    # Read-only views
    @property
    def soc(self):
        return self._energy_wh / CAPACITY_WH

    @property
    def energy_wh(self):
        return self._energy_wh

    @property
    def temp_c(self):
        return self._temp_c

    def available_for_tasks(self):
        """Energy a task may use: everything above the reserve."""
        return max(0.0, self._energy_wh - RESERVE_WH)

    @staticmethod
    def motion_energy_wh(degrees, wh_per_degree, seconds):
        """Energy for a motion: per-degree cost + idle draw over the time."""
        if (not all(_finite_number(v) for v in (degrees, wh_per_degree, seconds))
                or wh_per_degree < 0 or seconds < 0):
            raise ValueError("motion inputs must be finite with nonnegative cost and duration")
        energy = abs(degrees) * wh_per_degree + IDLE_W * seconds / 3600.0
        if not _finite_number(energy):
            raise ValueError("motion energy must be finite")
        return energy

    def draw_task(self, wh):
        """Use energy for a task. Refuses (False) if it would touch the reserve."""
        if not _finite_number(wh) or wh < 0 or wh > self.available_for_tasks():
            return False
        self._use(wh)
        return True

    def draw_reserve(self, wh):
        """Only the safe stop may call this. Uses the reserve if needed."""
        if not _finite_number(wh) or wh < 0:
            raise ValueError("reserve draw must be a finite nonnegative number")
        self._use(min(wh, self._energy_wh))

    def _use(self, wh):
        self._energy_wh -= wh
        self._temp_c += wh * HEAT_C_PER_WH

    def cool(self, seconds):
        if not _finite_number(seconds) or seconds < 0:
            raise ValueError("cooling duration must be a finite nonnegative number")
        self._temp_c -= (self._temp_c - AMBIENT_C) * min(1.0, COOL_PER_S * seconds)

    def check(self, monitor):
        """Raise MONITOR faults for low battery / over-temperature.
        A fault is only raised once while active (so it doesn't count as a repeat)."""
        if self.soc < LOW_SOC and "LOW_BATTERY" not in monitor.faults:
            monitor.raise_fault("LOW_BATTERY", "SoC %.0f%%" % (self.soc * 100))
        if self._temp_c > OVER_TEMP_C and "OVER_TEMP" not in monitor.faults:
            monitor.raise_fault("OVER_TEMP", "%.1f °C" % self._temp_c, critical=True)
