[Setup]
AppName=YT Music Downloader
AppVersion=1.0
DefaultDirName={autopf}\YT Music Downloader
DefaultGroupName=YT Music Downloader
AppPublisher=Khush
UninstallDisplayIcon={app}\ytmp3.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
OutputBaseFilename=YTMusicDownloader_Setup
PrivilegesRequired=admin
AllowCancelDuringInstall=no
LicenseFile=
SetupIconFile=static\favicon.ico

[Files]
Source: "dist\ytmp3.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\YT Music Downloader"; Filename: "{app}\ytmp3.exe"
Name: "{autodesktop}\YT Music Downloader"; Filename: "{app}\ytmp3.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:";
