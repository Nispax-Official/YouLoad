#define AppName "YouLoad"
#define AppPublisher "NISPAX InfoTech"
#define AppVersion GetEnv("YOULOAD_VERSION")
#define AppExeName "YouLoad.exe"

[Setup]
AppId={{A6D27D71-1B48-4C52-8A3B-7D4A8A4B6F10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\YouLoad
DefaultGroupName={#AppName}
OutputDir=..\release
OutputBaseFilename=YouLoad-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\ui\assets\youload-icon.ico
LicenseFile=..\LICENSE

[Files]
Source: "..\dist\YouLoad\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\YouLoad"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\YouLoad"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch YouLoad"; Flags: nowait postinstall skipifsilent
