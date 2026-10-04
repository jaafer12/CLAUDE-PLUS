; ملف تثبيت «صورة رسمية» — يُبنى عبر tools/build.py الذي يمرّر رقم الإصدار:
;   ISCC /DAppVersion=1.0.0 /DSourceDir=..\dist\IDPhoto /DIconFile=..\build\app.ico IDPhoto.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\IDPhoto"
#endif
#ifndef IconFile
  #define IconFile "..\build\app.ico"
#endif

#define AppName "صورة رسمية"
#define AppExe "IDPhoto.exe"

[Setup]
; لا تغيّر AppId: به يتعرّف المثبّت على النسخة القديمة فيحدّثها بدلاً من تثبيت نسخة ثانية
AppId={{8C1F3E52-6A3B-4C2E-9F3D-1D2B7A9E4C10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=IDPhoto
VersionInfoVersion={#AppVersion}
VersionInfoProductName=IDPhoto
DefaultDirName={autopf}\IDPhoto
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputBaseFilename=IDPhoto-{#AppVersion}-Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; التثبيت للمستخدم الحالي بلا صلاحيات مدير، فيعمل التحديث التلقائي بصمت
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Languages]
#if FileExists(AddBackslash(CompilerPath) + "Languages\Arabic.isl")
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; حذف ملفات الإصدار السابق قبل نسخ الجديد حتى لا تبقى مكتبات قديمة
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; بلا skipifsilent: بعد التحديث الصامت من داخل البرنامج يُعاد فتحه تلقائياً
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall
