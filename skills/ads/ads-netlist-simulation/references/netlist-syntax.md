# ADS native netlist syntax

Use this as a compact routing guide. The controller synopses below were checked against ADS 2025 Update 2 `hpeesofsim -h`. Component examples also match an ADS-generated netlist. For unfamiliar models or advanced controller options, query ADS Help RAG or run `hpeesofsim -h <token>` instead of guessing.

## File and statement basics

- `netlist.log` is a conventional ADS-generated filename; hpeesofsim accepts another input filename.
- Use `;` for full-line comments in ADS-generated netlists.
- Use node `0` as ground.
- Continue a long statement with a trailing `\`.
- Attach units to values, such as `50 Ohm`, `1 pF`, `1 GHz`, `200 uA`, or use an expression/variable.
- Define top-level variables with `Name=value`; use `global Name = value unit` when global visibility is required.
- Keep an `Options` statement with `TopDesignName="library:cell:view"`. The cell portion normally determines the `.ds` filename.

```text
; minimal structure, not a complete circuit
Options ResourceUsage=yes TopDesignName="demo_lib:demo:schematic"
global Vbias = 0 V
Vstart=0
Vstop=5
Vstep=0.1
```

## Instances and models

The general device form reported by the built-in help is:

```text
DeviceType:InstanceName node1 node2 ... Parameter=value ...
```

Checked primitive forms:

```text
R:R1 in out R=50 Ohm
C:C1 out 0 C=1 pF
V_Source:V1 in 0 Type="V_DC" Vdc=Vbias SaveCurrent=yes
I_Source:I1 0 out Type="I_DC" Idc=100 uA
Port:P1 in 0 Num=1 Z=50 Ohm
```

ADS model cards use `model ModelName ModelType ...`; a model-backed instance starts with the quoted model name. This BJT pattern is taken from an ADS-generated netlist:

```text
model BJTM1 BJT NPN=1 PNP=0 Is=4.08e-16 Bf=166 Vaf=25 Tnom=25
"BJTM1":Q1 collector base 0 Mode=1 Noise=yes
```

Do not generalize BJT parameters to another model family. Retrieve the exact model/device help or generate one instance from ADS, then copy its node order and parameter tokens.

## Sweep plans

`SweepPlan` supplies values to a simulator or `ParamSweep`. Built-in syntax:

```text
SweepPlan:linear_plan Start=0 Stop=5 Step=0.1
SweepPlan:linear_count Start=0 Stop=5 Lin=51
SweepPlan:log_plan Start=1 MHz Stop=10 GHz Dec=20
SweepPlan:points Pt=1 GHz Pt=2 GHz Pt=2.5 GHz
```

Use a quoted variable name in `SweepVar`. A sweep plan overrides sweep values configured directly on a controller. A `ParamSweep` must name the analysis instances it controls:

```text
ParamSweep:outer SimInstanceName[1]="DC1" SweepVar="Ibias" SweepPlan="ibias_plan"
SweepPlan:ibias_plan Start=20 uA Stop=200 uA Step=20 uA
```

Start a parameter sweep near an expected converged point and change it gradually when convergence is difficult.

## DC

Built-in synopsis: `DC [:Name] <parameter=value> ...`.

```text
DC:DC1 SweepVar="Vbias" SweepPlan="dc_plan" Restart=1 StatusLevel=2
SweepPlan:dc_plan Start=Vstart Stop=Vstop Step=Vstep
```

Useful exact parameters include `SweepVar`, repeatable `SweepPlan[]`, `MaxIters`, `Restart`, `PrintOpPoint`, `DevOpPtLevel`, `OutVar`, and `OutputPlan`.

## AC

Built-in synopsis: `AC [:Name] <parameter=value> ...`.

Single point:

```text
AC:AC1 Freq=1 GHz CalcNoise=no StatusLevel=2
```

Frequency sweep:

```text
AC:AC1 SweepVar="freq" SweepPlan="ac_freq" CalcNoise=no
SweepPlan:ac_freq Start=1 MHz Stop=10 GHz Dec=20
```

Use an independent source with `Vac` or `Iac` for small-signal excitation. Useful exact parameters include `Freq`, `SweepVar`, repeatable `SweepPlan[]`, `CalcNoise`, `NoiseNode`, `BandwidthForNoise`, `OutVar`, and `OutputPlan`.

## S-parameters

The controller token is `S_Param`, not `SP`. Built-in synopsis: `S_Param [:Name] <parameter=value> ...`.

```text
Port:P1 in 0 Num=1 Z=50 Ohm
Port:P2 out 0 Num=2 Z=50 Ohm
S_Param:SP1 SweepVar="freq" SweepPlan="sp_freq" CalcS=yes CalcY=no CalcZ=no
SweepPlan:sp_freq Start=1 MHz Stop=10 GHz Dec=20
```

Useful exact parameters include `Freq`, `SweepVar`, repeatable `SweepPlan[]`, `CalcS`, `CalcY`, `CalcZ`, `CalcNoise`, `NoiseInputPort`, `NoiseOutputPort`, `CalcGroupDelay`, and `SaveToDataset`.

## Harmonic balance

The controller token is `HB`. Built-in synopsis: `HB [:Name] <parameter=value> ...`.

```text
HB:HB1 Freq[1]=1 GHz Order[1]=5 MaxOrder=5 StatusLevel=2
```

For multiple fundamentals, repeat indexed `Freq[]` and `Order[]` and verify `NumberOfFunds`/`MaxOrder` against the intended mixing products. Large-signal source harmonic parameters are model-specific enough that the safest route is to export a minimal ADS schematic containing the desired source and HB controller.

Useful exact HB parameters include `Freq[]`, `Order[]`, `MaxOrder`, `NumberOfFunds`, `SweepVar`, repeatable `SweepPlan[]`, `MaxIters`, `Restart`, `UseKrylov`, `InitGuess`, `TAHB_Enable`, `OutVar`, and `OutputPlan`. When sweeping, keep `Restart` disabled if the prior solution should seed the next point.

## Subcircuits and includes

Native ADS subcircuits use `define`, optional `parameters`, and `end` rather than SPICE `.SUBCKT/.ENDS`. Exact port order and invocation syntax should come from an ADS-generated example or ADS Help RAG. ADS does not support nested native subcircuit definitions in the same way as some SPICE dialects.

Resolve relative include paths from the simulator working directory. Prefer an absolute include path in automated runs unless portability requires a controlled relative layout.

## Retrieve exact syntax

Use the cheapest reliable source in this order:

1. Reuse a working ADS-generated `netlist.log` for the same component/controller.
2. Run `hpeesofsim -h <token>` for a known simulator/device token, for example `DC`, `AC`, `S_Param`, `HB`, `SweepPlan`, `ParamSweep`, `Port`, or `BJT`.
3. Query ADS Help RAG `search_docs` with `category="simulation"` and the exact token plus the intended behavior.
4. Generate a one-component or one-controller schematic in ADS and compare its netlist when documentation does not show the emitted form.

Never infer node order, array indices, or advanced model parameters from a different device family.
