# My Switcher 0.1 — prototype for Windows 10/11
import ctypes, json, os, sys, time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "MySwitcher"
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG = APP_DIR / "settings.json"
DICT = APP_DIR / "dictionary.txt"
DEFAULT = {
 "ru": set("привет здравствуйте спасибо пожалуйста сегодня завтра работа компьютер программа клавиатура раскладка слово текст сообщение русский украинский английский язык проверка пример ошибка исправить отмена настройки приложение пароль хорошо можно нужно да нет как что это мой твой наш время деньги человек люди сайт ссылка браузер окно файл запуск словарь".split()),
 "ua": set("привіт доброго дякую будь ласка сьогодні завтра робота компютер програма клавіатура розкладка слово текст повідомлення український англійський мова перевірка приклад помилка виправити скасувати налаштування застосунок пароль добре можна потрібно так ні як що це мій твій наш час гроші люди сайт посилання браузер вікно файл запуск словник".split()),
 "en": set("hello hi thanks please today tomorrow work computer program keyboard layout word text message russian ukrainian english language test check example error correct undo settings application password good can need yes no what this my your our time money people website link browser window file launch dictionary".split())
}
# QWERTY physical-key approximation; punctuation varies across Windows layouts.
EN = "`qwertyuiop[]asdfghjkl;'zxcvbnm,./"
RU = "ёйцукенгшщзхъфывапролджэячсмитьбю."
UA = "'йцукенгшщзхїфівапролджєячсмитьбю."
MAPS = {
 ("en","ru"): dict(zip(EN,RU)), ("ru","en"): {v:k for k,v in dict(zip(EN,RU)).items()},
 ("en","ua"): dict(zip(EN,UA)), ("ua","en"): {v:k for k,v in dict(zip(EN,UA)).items()}
}
MAPS[("ru","ua")] = {c: MAPS[("en","ua")].get(MAPS[("ru","en")].get(c,c),c) for c in RU}
MAPS[("ua","ru")] = {c: MAPS[("en","ru")].get(MAPS[("ua","en")].get(c,c),c) for c in UA}
def convert(word, src, dst):
    m = MAPS.get((src,dst),{})
    return "".join((m.get(ch.lower(),ch).upper() if ch.isupper() else m.get(ch,ch)) for ch in word)
def load():
    s={"enabled":True,"startup":False,"excluded_apps":["code.exe","devenv.exe","powershell.exe","cmd.exe","windowsterminal.exe"]}
    try: s.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    except Exception: pass
    words={k:set(v) for k,v in DEFAULT.items()}
    if not DICT.exists():
        DICT.write_text("# Format: ru слово1 слово2 | ua слово1 слово2 | en word1 word2\nru привет спасибо пожалуйста\nua привіт дякую будь ласка\nen hello thanks please\n",encoding="utf-8")
    for line in DICT.read_text(encoding="utf-8").splitlines():
        p=line.strip().lower().split()
        if len(p)>1 and p[0] in words: words[p[0]].update(p[1:])
    return s,words
def foreground_exe():
    try:
        u=ctypes.windll.user32; k=ctypes.windll.kernel32
        hwnd=u.GetForegroundWindow(); pid=ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        h=k.OpenProcess(0x1000,False,pid.value)
        if not h:return ""
        try:
            b=ctypes.create_unicode_buffer(32768); n=ctypes.c_ulong(len(b))
            return os.path.basename(b.value).lower() if k.QueryFullProcessImageNameW(h,0,b,ctypes.byref(n)) else ""
        finally:k.CloseHandle(h)
    except Exception:return ""
class App:
 def __init__(self):
    self.settings,self.words=load(); self.buffer=""; self.inject=False; self.last=None; self.listener=None
    self.root=tk.Tk(); self.root.title("My Switcher"); self.root.geometry("490x430")
    self.enabled=tk.BooleanVar(value=self.settings["enabled"]); self.startup=tk.BooleanVar(value=self.settings["startup"])
    f=ttk.Frame(self.root,padding=15); f.pack(fill="both",expand=True)
    ttk.Label(f,text="My Switcher",font=("Segoe UI",17,"bold")).pack(anchor="w")
    ttk.Label(f,text="Автоисправление раскладки RU · UA · EN").pack(anchor="w",pady=(0,10))
    self.status=tk.StringVar(value="Запуск…"); ttk.Label(f,textvariable=self.status).pack(anchor="w",pady=5)
    ttk.Checkbutton(f,text="Автоисправление включено",variable=self.enabled,command=self.save).pack(anchor="w",pady=3)
    ttk.Checkbutton(f,text="Запускать вместе с Windows",variable=self.startup,command=self.set_startup).pack(anchor="w",pady=3)
    ttk.Label(f,text="Исключённые .exe (через запятую):").pack(anchor="w",pady=(10,3))
    self.ex=ttk.Entry(f);self.ex.pack(fill="x");self.ex.insert(0,", ".join(self.settings["excluded_apps"]))
    ttk.Button(f,text="Сохранить исключения",command=self.save_ex).pack(anchor="w",pady=5)
    r=ttk.Frame(f);r.pack(anchor="w",pady=5)
    ttk.Button(r,text="Открыть словарь",command=self.open_dict).pack(side="left")
    ttk.Button(r,text="Добавить слово",command=self.add_word).pack(side="left",padx=5)
    ttk.Button(r,text="Отмена последнего исправления",command=self.undo).pack(side="left")
    ttk.Separator(f).pack(fill="x",pady=10)
    ttk.Label(f,text="Прототип: исправление после пробела, только при единственном совпадении в локальном словаре.").pack(anchor="w")
    ttk.Label(f,text="Обработка выполняется локально.").pack(anchor="w",pady=3)
    self.root.protocol("WM_DELETE_WINDOW",self.root.iconify)
    self.start_listener(); self.root.mainloop()
 def save(self):
    self.settings["enabled"]=self.enabled.get(); CONFIG.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding="utf-8")
 def set_startup(self):
    self.settings["startup"]=self.startup.get();self.save()
    try:
      import winreg
      key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",0,winreg.KEY_SET_VALUE)
      if self.startup.get(): winreg.SetValueEx(key,"MySwitcher",0,winreg.REG_SZ,f'"{sys.executable}"')
      else:
        try: winreg.DeleteValue(key,"MySwitcher")
        except FileNotFoundError: pass
      winreg.CloseKey(key)
    except Exception as e: messagebox.showwarning("Автозапуск",str(e))
 def save_ex(self):
    self.settings["excluded_apps"]=[x.strip().lower() for x in self.ex.get().split(",") if x.strip()];self.save()
    messagebox.showinfo("My Switcher","Исключения сохранены")
 def open_dict(self):
    try: os.startfile(str(DICT))
    except Exception as e: messagebox.showerror("Словарь",str(e))
 def add_word(self):
    lang=simpledialog.askstring("Язык","Введите ru, ua или en")
    if not lang or lang.lower() not in self.words:return
    word=simpledialog.askstring("Слово","Введите слово")
    if word:
      with DICT.open("a",encoding="utf-8") as f:f.write(f"\n{lang.lower()} {word.lower()}\n")
      self.words[lang.lower()].add(word.lower())
 def start_listener(self):
    try:
      from pynput import keyboard
      self.keyboard=keyboard; self.controller=keyboard.Controller()
      self.listener=keyboard.Listener(on_press=self.on_press);self.listener.daemon=True;self.listener.start()
      self.status.set("Работает локально · RU / UA / EN")
    except Exception as e:self.status.set("Ошибка клавиатурного модуля: "+str(e))
 def on_press(self,key):
    if self.inject or not self.settings.get("enabled",True):return
    try:
      if key==self.keyboard.Key.space or key in (self.keyboard.Key.enter,self.keyboard.Key.tab,self.keyboard.Key.period,self.keyboard.Key.comma,self.keyboard.Key.semicolon,self.keyboard.Key.colon,self.keyboard.Key.exclamation_mark,self.keyboard.Key.question_mark):
        w=self.buffer;self.buffer=""
        if len(w)>=4 and foreground_exe() not in self.settings.get("excluded_apps",[]):self.correct(w)
      elif key==self.keyboard.Key.backspace:self.buffer=self.buffer[:-1]
      elif key in (self.keyboard.Key.shift,self.keyboard.Key.shift_l,self.keyboard.Key.shift_r,self.keyboard.Key.ctrl,self.keyboard.Key.ctrl_l,self.keyboard.Key.ctrl_r,self.keyboard.Key.alt,self.keyboard.Key.alt_l,self.keyboard.Key.alt_r):pass
      else:
        c=getattr(key,"char",None)
        if c and c.isalpha():self.buffer=(self.buffer+c)[-64:]
        elif c:self.buffer=""
    except Exception:pass
 def correct(self,w):
    low=w.lower()
    if any(low in self.words[l] for l in self.words):return
    cands=set()
    for s in ("ru","ua","en"):
      for d in ("ru","ua","en"):
        if s!=d:
          c=convert(low,s,d).lower()
          if c!=low and c in self.words[d]:cands.add((c,d))
    if len(cands)!=1:return
    c,_=next(iter(cands)); new=c.upper() if w.isupper() else c.capitalize() if w[:1].isupper() else c
    self.inject=True
    try:
      for _ in w:self.controller.tap(self.keyboard.Key.backspace)
      self.controller.type(new);self.last=(w,new,time.time())
    finally:self.inject=False
 def undo(self):
    if not self.last or time.time()-self.last[2]>60:
      messagebox.showinfo("Отмена","Нет недавнего исправления");return
    old,new,_=self.last;self.inject=True
    try:
      for _ in new:self.controller.tap(self.keyboard.Key.backspace)
      self.controller.type(old);self.last=None
    finally:self.inject=False
if __name__=="__main__":
    if os.name!="nt": print("Windows 10/11 only")
    App()
