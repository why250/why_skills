# Cross-version AEL netlisting

Read this file when generating netlist.log from an ADS schematic path or changing the AEL launcher.

## Capability boundary

hpeesofsim consumes a simulator netlist but cannot read an OpenAccess schematic. Schematic-to-netlist conversion needs ADS Design Environment and a valid DesignContext.

The bundled launcher uses no Python:

    ads.exe -m generate_netlist.ael

ADS loads the startup AEL in SimCmd; the script opens the workspace, resolves the logical library/cell/view, creates the netlist, saves it, closes the workspace, and exits ADS. The ADS process is hidden but still exists, so describe this as command-line automation, not a GUI-free or headless netlister.

## Cross-version API set

Use only these documented APIs:

| AEL API | Introduced |
| --- | --- |
| de_open_workspace | ADS 2011 |
| de_get_design_context_from_name | ADS 2011 |
| de_netlist_create | ADS 2011 |
| de_netlist_save | ADS 2011 |
| de_close_workspace_without_prompting | ADS 2011 |
| de_exit | legacy ADS Design Environment |
| getsysenv | legacy AEL system environment access |
| getpid | ADS 2022 Update 1 |

Do not replace de_get_design_context_from_name with db_get_design_context_from_name when ADS 2022 support is required. The replacement was introduced only in ADS 2023 Update 2; the older function is deprecated in newer ADS but retained.

## Path mapping

Input physical layout:

    <workspace>\<library>\<physical-cell>\<view>

AEL requires:

    library:logical-cell:view

ADS/OpenAccess physical directories may prefix case-sensitive characters with a percent marker. The launcher maps:

    %B%J%T_%I%V_%Gm_%Power%Calcs
    BJT_IV_Gm_PowerCalcs

Pass -CellName explicitly when a library uses a different physical-name mapping. Do not guess after ADS reports ERROR_DESIGN.

## Session safety

Before launching ads.exe -m, generate_netlist.ps1 records every existing hpeesofde PID. The startup AEL compares its own getpid() value with that protected list before opening a workspace. If ADS routes the AEL into a pre-existing process, it writes ERROR_REUSED_SESSION and returns without calling de_open_workspace, de_close_workspace_without_prompting, or de_exit.

getpid() requires ADS 2022 Update 1 or newer. If an earlier ADS build lacks getpid and another ADS session is already running, the AEL writes ERROR_PID_UNAVAILABLE and returns without touching that session. Netlisting still works on such builds when no ADS session was already open.

The PowerShell launcher observes only hpeesofde PIDs that were absent before invocation. Exit waiting and failure cleanup apply only to those new PIDs; never terminate a protected pre-existing PID.

The launcher exchanges arguments through temporary system environment variables and success through a temporary status file. Run ads.exe in a unique directory under the system temporary directory so ADS startup files such as de_sim.cfg and hpeesofsim.cfg never appear in the caller's current directory. Remove that private directory after the new ADS process exits. Validate that the final netlist exists and is nonempty before reporting NETLIST_PATH.
