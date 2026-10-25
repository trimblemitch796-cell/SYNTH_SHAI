# SHAI digital twin + ELO-ECTRIC power model

> **Software-only simulation. NOT hardware-ready.** There are no motors, serial ports or network.
> **Every joint limit, speed, torque, energy cost, battery and temperature value is an illustrative EXAMPLE, not an engineering spec.**
> Real hardware would need its own design, hazard analysis, certified parts, a physical ESTOP and independent review.

## The twin (`shai/twin.py`)

- A simulated humanoid about **170 cm** tall, with 9 example joints: neck, shoulders, elbows, hips and knees. Each joint has an
  angle range, a max speed (°/s), a max torque (Nm) and an energy cost (Wh per degree).
- Simulated sensors: camera and lidar distance to a wall 2 m away, IMU tilt, joint encoders, foot contact and pack temperature.
  Camera and lidar produce readings in the CHECK EVIDENCE / TRIANGULATE format, with `source` and `type`.
- A fixed 0.1 s timestep, a fake clock with no real sleeps, and seeded randomness, so every run is the same.

### The only way to move: `request_motion(plan, approval, provenance, ethical_evidence)`

A joint moves **only if all** of these are true:

1. The plan is valid, and every joint stays inside its angle, speed and torque limits.
2. The battery has enough energy **above the safe-stop reserve**.
3. MANIAC `run_loop()` ends **BALANCED** with `HUMAN_REVIEW`. That means USHAI, the monitor, CHECK EVIDENCE with freshly signed V3.1
   provenance, TRIANGULATE, VERIFY, RE-OBSERVE, LEARN and AUDIT all passed.
4. A human `record_human_decision(..., "APPROVED", ...)` was recorded for **this exact request id**.

Anything else gives `144 HOLD`, or `SAFE_LOCK`, and **nothing moves**. Request ids can't be reused. An approval for a
different request is refused. The joint angles you can read are a copy, and the read-only properties can't be set. Note that
Python can't truly hide `_private` attributes. This is a code-review rule, not a security boundary.

The motion runs in 0.1 s steps. If the monitor leaves `MONITOR` mid-motion (for example a sensor drops out), the twin does a
**safe stop**: joints halt where they are, using energy from the reserve. Then it returns HOLD, or SAFE_LOCK for a critical fault.

## ELO-ECTRIC power model (`shai/power.py`)

| Example value | Setting |
| --- | --- |
| Pack | 2 kWh (2000 Wh) |
| Safe-stop reserve | 100 Wh, never available to tasks |
| Idle draw | 60 W |
| Low battery | below 15 % charge gives a `LOW_BATTERY` fault, which means 144 HOLD |
| Heat | +0.5 °C per Wh used, cooling 1 % of the gap to 25 °C ambient per second |
| Over-temperature | above 60 °C gives a critical `OVER_TEMP` fault, which means SAFE_LOCK |

## Simulation scenarios

`python3 -m maniac.simulation` includes 7 twin scenarios:

| Scenario | Result |
| --- | --- |
| An approved 30° elbow move | MOVED |
| No approval | HOLD |
| A move over the joint limit | HOLD |
| 10 % battery | HOLD |
| 65 °C pack | SAFE_LOCK |
| Lidar dropout mid-motion | HOLD + safe stop |
| An approval for a different request | HOLD |

## Run the tests

```bash
python3 -m unittest -v test_shai_twin test_shai_power
```
