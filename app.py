import csv, io, json, os, re, subprocess, sys, tempfile, threading, unicodedata, webbrowser
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
import tkinter as tk
from tkinter import ttk, messagebox

VERSION = '1.0.1'
REPOSITORY = 'funny4875/ExtensionFinder'
DEFAULT_URL = 'https://docs.google.com/spreadsheets/d/1Lct4-RYD9BnXr5FQcZGVMypbT2Q4OwIukyN0Fliut3Y/edit?gid=1015890817#gid=1015890817'
CONFIG = Path(os.getenv('APPDATA', str(Path.home()))) / 'ExtensionFinder' / 'settings.json'

def export_url(url):
    p=urlparse(url.strip())
    m=re.fullmatch(r'/spreadsheets/d/([\w-]+)(?:/.*)?', p.path)
    if p.scheme != 'https' or p.hostname != 'docs.google.com' or not m:
        raise ValueError('請貼上完整的 Google 試算表網址。')
    gid=parse_qs(p.query).get('gid', [''])[0] or parse_qs(p.fragment).get('gid', [''])[0] or '0'
    if not gid.isdigit(): raise ValueError('工作表 gid 必須是數字。')
    return f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}'

def normalize(s): return ''.join(unicodedata.normalize('NFKC', str(s)).casefold().split())
def read_data(url):
    with urlopen(Request(export_url(url), headers={'User-Agent':'ExtensionFinder/'+VERSION}), timeout=20) as response:
        data=response.read().decode('utf-8-sig')
    if data.lstrip().lower().startswith(('<!doctype','<html')): raise ValueError('無法讀取工作表，請確認連結及分享權限。')
    rows=list(csv.reader(io.StringIO(data)))
    for index,row in enumerate(rows):
        header=[x.strip() for x in row]
        if all(x in header for x in ('職務','姓名','分機')):
            cols=[header.index(x) for x in ('職務','姓名','分機')]
            return [tuple(row[i].strip() if i<len(row) else '' for i in cols) for row in rows[index+1:] if any(row)]
    raise ValueError('找不到「職務」、「姓名」、「分機」欄位，請確認工作表。')

def search(rows, query):
    q=normalize(query); exact=[]; partial=[]; fuzzy=[]
    for row in rows:
        fields=[normalize(row[0]),normalize(row[1])]
        if q in fields: exact.append(row)
        elif any(q in x for x in fields if x): partial.append(row)
        else:
            score=max((SequenceMatcher(None,q,x).ratio() for x in fields if x),default=0)
            if len(q)>=2 and score>=.5: fuzzy.append((score,row))
    if exact:return '完全符合',exact
    if partial:return '包含關鍵字',partial
    fuzzy.sort(key=lambda x:-x[0]); return '相似結果，請確認',[x[1] for x in fuzzy[:20]]

def version_tuple(s):
    m=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)',s.strip())
    return tuple(map(int,m.groups())) if m else None

def latest_release():
    if not REPOSITORY: return None
    req=Request(f'https://api.github.com/repos/{REPOSITORY}/releases/latest',headers={'User-Agent':'ExtensionFinder/'+VERSION,'Accept':'application/vnd.github+json'})
    with urlopen(req,timeout=10) as r: release=json.load(r)
    v=version_tuple(release.get('tag_name',''))
    if not v or v<=version_tuple(VERSION): return None
    return release

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f'分機查詢 v{VERSION}');
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ExtensionFinder.Desktop.1')
            self.iconbitmap(str(Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'assets' / 'icon.ico'))
        except Exception: pass
        self.geometry('500x430'); self.minsize(440,350); self.configure(bg='#f1f6f6')
        self.url=DEFAULT_URL
        try:
            with CONFIG.open(encoding='utf-8') as f: self.url=json.load(f).get('url',DEFAULT_URL)
        except (OSError,ValueError,TypeError): pass
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('Treeview',font=('Microsoft JhengHei UI',10),rowheight=30,background='white',fieldbackground='white',borderwidth=0)
        style.configure('Treeview.Heading',font=('Microsoft JhengHei UI',9,'bold'),background='#e3efed',foreground='#315b57',relief='flat')
        frame=tk.Frame(self,bg='#f1f6f6',padx=22,pady=18); frame.pack(fill='both',expand=True)
        head=tk.Frame(frame,bg='#f1f6f6'); head.pack(fill='x')
        tk.Label(head,text='分機查詢',font=('Microsoft JhengHei UI',16,'bold'),fg='#173f3c',bg='#f1f6f6').pack(side='left')
        tk.Button(head,text='⚙ 設定連結',command=self.settings,bd=0,bg='#f1f6f6',fg='#33756d',font=('Microsoft JhengHei UI',9),cursor='hand2').pack(side='right')
        tk.Label(frame,text='輸入姓名或職務，快速找到分機',fg='#66827d',bg='#f1f6f6',font=('Microsoft JhengHei UI',9)).pack(anchor='w',pady=(2,12))
        line=tk.Frame(frame,bg='#f1f6f6'); line.pack(fill='x')
        self.entry=tk.Entry(line,font=('Microsoft JhengHei UI',12),relief='solid',bd=1); self.entry.pack(side='left',fill='x',expand=True,ipady=6)
        self.entry.bind('<Return>',lambda e:self.run_search())
        self.button=tk.Button(line,text='查詢',command=self.run_search,bg='#187d70',fg='white',activebackground='#12675d',activeforeground='white',bd=0,padx=18,pady=6,font=('Microsoft JhengHei UI',10,'bold'),cursor='hand2'); self.button.pack(side='left',padx=(8,0))
        self.status=tk.StringVar(value='每次查詢都會讀取最新資料')
        tk.Label(frame,textvariable=self.status,bg='#f1f6f6',fg='#67827e',font=('Microsoft JhengHei UI',9),anchor='w').pack(fill='x',pady=(12,7))
        table=tk.Frame(frame,bg='#f1f6f6'); table.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(table,columns=('job','name','ext'),show='headings',selectmode='browse')
        for col,title,width in [('job','職務',210),('name','姓名',110),('ext','分機',100)]:self.tree.heading(col,text=title); self.tree.column(col,width=width,anchor='w')
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set); self.tree.pack(side='left',fill='both',expand=True); scroll.pack(side='right',fill='y')
        tk.Label(frame,text='未填分機顯示「未提供」',bg='#f1f6f6',fg='#8aa09c',font=('Microsoft JhengHei UI',8)).pack(anchor='w',pady=(8,0))
        self.entry.focus_set(); self.after(1000,self.check_update)
    def settings(self):
        win=tk.Toplevel(self); win.title('設定工作表連結'); win.transient(self); win.resizable(False,False); win.configure(bg='#f1f6f6')
        box=tk.Frame(win,bg='#f1f6f6',padx=20,pady=18); box.pack(fill='both',expand=True)
        tk.Label(box,text='Google 試算表連結',bg='#f1f6f6',fg='#173f3c',font=('Microsoft JhengHei UI',11,'bold')).pack(anchor='w')
        tk.Label(box,text='請貼上要查詢的工作表連結，並確認可供讀取。',bg='#f1f6f6',fg='#66827d').pack(anchor='w',pady=(4,8))
        val=tk.StringVar(value=self.url); entry=tk.Entry(box,textvariable=val,width=65); entry.pack(fill='x',ipady=5)
        def save():
            try:
                export_url(val.get()); CONFIG.parent.mkdir(parents=True,exist_ok=True)
                CONFIG.write_text(json.dumps({'url':val.get().strip()},ensure_ascii=False,indent=2),encoding='utf-8'); self.url=val.get().strip(); win.destroy(); self.status.set('已儲存連結，請輸入姓名或職務查詢。')
            except (ValueError,OSError) as e: messagebox.showerror('無法儲存',str(e),parent=win)
        tk.Button(box,text='儲存',command=save,bg='#187d70',fg='white',bd=0,padx=20,pady=6).pack(anchor='e',pady=(12,0)); entry.focus_set(); win.grab_set()
    def run_search(self):
        q=self.entry.get().strip(); url=self.url
        if not q: messagebox.showinfo('提示','請輸入姓名或職務。',parent=self); return
        self.button.config(state='disabled'); self.status.set('正在讀取資料…'); self.tree.delete(*self.tree.get_children())
        def work():
            try:
                result=search(read_data(url),q); self.after(0,lambda:self.done(result))
            except Exception as e:
                msg=str(e); self.after(0,lambda:self.failed(msg))
        threading.Thread(target=work,daemon=True).start()
    def done(self,result):
        self.button.config(state='normal'); kind,rows=result
        for job,name,ext in rows:self.tree.insert('','end',values=(job,name,ext or '未提供'))
        self.status.set(f'{kind}：找到 {len(rows)} 筆' if rows else '找不到相符資料，請試試其他關鍵字。')
    def failed(self,msg):
        self.button.config(state='normal'); self.status.set('讀取失敗，請檢查連結和網路。'); messagebox.showerror('讀取失敗',msg,parent=self)
    def check_update(self):
        def work():
            try:
                release=latest_release()
                if release:self.after(0,lambda:self.offer_update(release))
            except Exception: pass
        threading.Thread(target=work,daemon=True).start()
    def offer_update(self,release):
        if messagebox.askyesno('有新版本',f"發現新版本 {release['tag_name']}（目前 {VERSION}）。\n要開啟下載頁面進行更新嗎？",parent=self):
            webbrowser.open(release['html_url'])

if __name__=='__main__':App().mainloop()

