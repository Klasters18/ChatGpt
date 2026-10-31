[Setup]
AppId={{E13C44A8-2E73-4E93-A6E8-4A8C3E97B5D1}
AppName=My Switcher
AppVersion=0.3.3
AppPublisher=My Switcher
DefaultDirName={autopf}\My Switcher
DefaultGroupName=My Switcher
UninstallDisplayIcon={app}\MySwitcher.exe
OutputDir=installer-output
OutputBaseFilename=MySwitcher-Setup-x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные ярлыки:"
Name: "startup"; Description: "Запускать вместе с Windows"; GroupDescription: "Параметры запуска:"

[Files]
Source: "dist\MySwitcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\My Switcher"; Filename: "{app}\MySwitcher.exe"
Name: "{autodesktop}\My Switcher"; Filename: "{app}\MySwitcher.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "MySwitcher"; ValueData: """{app}\MySwitcher.exe"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\MySwitcher.exe"; Description: "Запустить My Switcher"; Flags: postinstall nowait skipifsilent
