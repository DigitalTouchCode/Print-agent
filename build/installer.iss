; Build with Inno Setup (https://jrsoftware.org/isinfo.php):
;   Open this file in the Inno Setup Compiler and click Build,
;   or from the command line: iscc build\installer.iss
; Produces: build\output\dt-print-agent-setup.exe
; Run build\build.bat first so dist\DT Print Agent.exe exists.

#define MyAppName "DT Print Agent"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DigitalTouch"
#define MyAppExeName "DT Print Agent.exe"

[Setup]
AppId={{B6C1B1A0-6E1E-4C6C-9C7E-DTPRINTAGENT1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DigitalTouch\PrintAgent
DefaultGroupName=DigitalTouch
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=dt-print-agent-setup
SetupIconFile=..\assets\dt_icon.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
; ^ per-user install: no admin prompt, matches installing to a till PC a
; cashier account can run without IT help.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "Start DT Print Agent automatically when Windows starts"; GroupDescription: "Startup:"; Flags: checkedonce
Name: "runzadig"; Description: "Open the one-time USB driver setup (Zadig) after installing"; GroupDescription: "First-time setup:"; Flags: checkedonce

[Files]
Source: "..\dist\DT Print Agent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\dt_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "dt-print-agent-setup-guide.pdf"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
; Zadig itself isn't redistributed here — see the setup guide for the
; download link and interface-selection steps; ticking the task above
; just opens that guide.
Filename: "{app}\dt-print-agent-setup-guide.pdf"; Description: "Open the USB driver setup guide"; Flags: postinstall skipifsilent shellexec; Tasks: runzadig

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\..\Local\DigitalTouch\PrintAgent"
