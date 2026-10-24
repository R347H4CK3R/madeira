# Call of Duty HQ platform limitations

Evidence checked 2026-10-24. A successful Madeira bootstrap patch or a newly compiled IPA does not establish that Call of Duty HQ can launch or be played on jailed iOS.

## Confirmed vendor requirements

- Activision's RICOCHET overview, dated 2026-10-20, says its listed PC titles use a globally deployed kernel-level driver for all players. FAQ 12 says that driver is required to play a protected game; FAQ 6 describes automatic installation and startup with the game. The listed titles include Modern Warfare II/III, Warzone and Black Ops 6/7. [Activision support: RICOCHET overview](https://support.activision.com/articles/ricochet-overview)
- The publisher-controlled Steam listing for the exact **app 1938090** identifies Call of Duty and explicitly lists **RICOCHET kernel-level anti-cheat**. Its current listing also identifies Secure Boot and TPM 2.0 requirements. This links the platform requirement to the app ID, rather than merely to another title in the franchise. [Call of Duty on Steam](https://store.steampowered.com/app/1938090/)
- Call of Duty's own RICOCHET page describes the PC kernel driver, its client/server protection, and hardware security integration. [Official RICOCHET page](https://www.callofduty.com/ricochet)

## What Randgrid evidence does and does not prove

The supplied device log directly shows app1938090's pending prerequisite `randgrid_install` (line55), then invocation of `bootstrapper_installer.exe atvi-randgrid_sr true Randgrid.sys` (line2923). It reports the prerequisite failed with -1073741795, i.e. 0xc000001d, and was **not recorded as installed** (line3998). Its CRT/bootstrap crash happens before the log establishes successful driver/service operation.

Searches of official Activision, Call of Duty, Blizzard and publisher Steam pages found no vendor documentation explicitly naming Randgrid.sys as the RICOCHET kernel driver. Therefore:

- **Proven:** this installation attempts a Randgrid.sys prerequisite, and the exact Steam product requires RICOCHET kernel-level anti-cheat.
- **Plausible but not established by the official sources:** Randgrid.sys is the specific mandatory RICOCHET kernel driver for this installed build.
- **Not proven by this log:** a Randgrid kernel-driver load was attempted and failed, or which later enforcement stage the application would reach after the CRT problem is fixed.

The .sys suffix and service-like arguments alone are insufficient to prove the driver's identity or its complete requirements. Community posts and independent-advisor answers were excluded as vendor proof.

## Madeira/Wine implication

Wine is a user-mode compatibility layer translating Windows APIs to its host operating system, rather than providing the Windows kernel. Wine's own developer record explains the distinction: limited driver compatibility does not grant actual host kernel privileges. [Wine project description](https://www.winehq.org/), [Wine developer explanation](https://list.winehq.org/hyperkitty/list/wine-bugs%40list.winehq.org/thread/RNMLZBQCE2VSMS43ATR624OTZTWWXUEI/)

The inspected pinned Wine source (`4f5b19718f4de88ecc5cb0dc08b119497a67ba8f`) has `NtLoadDriver` return STATUS_NOT_IMPLEMENTED. It also has a user-space winedevice route for some SERVICE_KERNEL_DRIVER and SERVICE_FILE_SYSTEM_DRIVER services. Thus the stub by itself does not prove every .sys file is unloadable; neither route supplies an actual Windows kernel or demonstrates compatibility with RICOCHET's proprietary required protections. [Pinned NtLoadDriver source](https://github.com/willfaust/wine/blob/4f5b19718f4de88ecc5cb0dc08b119497a67ba8f/dlls/ntdll/unix/system.c#L4697), [Pinned Wine service route](https://github.com/willfaust/wine/blob/4f5b19718f4de88ecc5cb0dc08b119497a67ba8f/programs/services/services.c#L964)

**Engineering conclusion:** the early CRT fix can address a source-supported loader failure and expose the next genuine result. It does not meet or remove the vendor's kernel-driver requirement. Call of Duty gameplay remains unverified and faces a material platform limitation. Do not report “COD fixed” or bypass installer/anti-cheat outcomes; preserve the prerequisite's true exit status and distinguish bootstrap, game launch, and gameplay evidence.
