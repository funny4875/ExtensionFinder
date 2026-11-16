# ExtensionFinder 分機查詢

Windows 電話分機查詢工具，可設定 Google 試算表連結，輸入姓名或職務查詢。優先顯示完全符合，沒有時再顯示包含關鍵字或相似結果。工作表需包含「職務」、「姓名」、「分機」欄位，且可不登入直接讀取。每次查詢會重新讀取工作表。

## 安裝與使用

從 [Releases](https://github.com/funny4875/ExtensionFinder/releases/latest) 下載 MSI 安裝檔。安裝後會在桌面和開始選單建立捷徑。開啟程式後可由右上角設定連結；原始預設工作表已帶入。程式啟動時會檢查新版，有新版會詢問是否開啟下載頁面，下載並執行新版 MSI 以更新。更新檢查失敗時不影響查詢。

設定儲存在目前使用者的 `%APPDATA%\ExtensionFinder\settings.json`。本程式需要連線網路，且不支援需要登入才能讀取的試算表。

## 建置

需要 Python 3、PyInstaller 及 WiX 5。圖示使用 `assets/icon.ico`。

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name ExtensionFinder --icon assets\icon.ico --add-data 'assets\icon.ico;assets' --distpath dist --workpath build app.py
wix build installer.wxs -o ExtensionFinder-1.0.3.msi
```
