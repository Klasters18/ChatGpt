# My Switcher 0.1 — prototype for Windows 10/11
import ctypes, json, os, sys, time, traceback
import tkinter as tk
import threading
import queue
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from grammar_check import check_text, GrammarServiceError

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "MySwitcher"
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG = APP_DIR / "settings.json"
DICT = APP_DIR / "dictionary.txt"
LOG = APP_DIR / "debug.log"
def log_debug(message):
    try:
        with LOG.open("a", encoding="utf-8") as fp: fp.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(message) + "\n")
    except Exception: pass
from layout_engine import get_engine, script_of
from win_input import send_backspaces, send_unicode_text, key_state

def load():
    s={"enabled":True,"startup":False,"excluded_apps":["code.exe","devenv.exe","powershell.exe","cmd.exe","windowsterminal.exe"]}
    try: s.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    except Exception: pass
    words={k:set() for k in ("ru","ua","en")}
    if not DICT.exists():
        DICT.write_text("# Personal words only; format: ru слово1 слово2 | ua слово1 слово2 | en word1 word2\n",encoding="utf-8")
    for line in DICT.read_text(encoding="utf-8").splitlines():
        p=line.strip().lower().split()
        if len(p)>1 and p[0] in words: words[p[0]].update(p[1:])
    return s,words
def foreground_window():
    try:
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        return user32.GetForegroundWindow()
    except Exception:
        return 0

def foreground_exe():
    try:
        u=ctypes.windll.user32; k=ctypes.windll.kernel32
        if key == self.keyboard.Key.caps_lock:
         log_debug("physical CapsLock press; toggle_state=" + str(key_state(0x14)) + "; foreground=" + foreground_exe())
       elif key in (self.keyboard.Key.shift,self.keyboard.Key.shift_l,self.keyboard.Key.shift_r):
         log_debug("physical Shift press; caps_lock=" + str(key_state(0x14)) + "; foreground=" + foreground_exe())
       hwnd=foreground_window(); pid=ctypes.c_ulong()
        if not hwnd:return ""
        u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        h=k.OpenProcess(0x1000,False,pid.value)
        if not h:return ""
        try:
            b=ctypes.create_unicode_buffer(32768); n=ctypes.c_ulong(len(b))
            return os.path.basename(b.value).lower() if k.QueryFullProcessImageNameW(h,0,b,ctypes.byref(n)) else ""
        finally:k.CloseHandle(h)
    except Exception:return ""

def activate_layout(lang):
    """Ask the foreground Windows text application to activate the target keyboard layout."""
    if os.name != "nt":
        return False
    klid = {"en": "00000409", "ru": "00000419", "ua": "00000422"}.get(lang)
    hwnd = foreground_window()
    if not klid or not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.LoadKeyboardLayoutW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
        user32.LoadKeyboardLayoutW.restype = ctypes.c_void_p
        user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        user32.PostMessageW.restype = ctypes.c_int
        hkl = user32.LoadKeyboardLayoutW(klid, 0x00000001)  # KLF_ACTIVATE
        if not hkl:
            log_debug("keyboard layout not available: " + lang + " (" + klid + ")")
            return False
        # WM_INPUTLANGCHANGEREQUEST; post to the actual foreground application.
        ok = user32.PostMessageW(hwnd, 0x0050, 0, hkl)
        log_debug("requested keyboard layout " + lang + "; posted=" + str(bool(ok)))
        return bool(ok)
    except Exception as e:
        log_debug("layout switch exception: " + repr(e))
        return False
class App:
 def __init__(self):
    self.settings,self.words=load(); self.buffer=""; self.buffer_hwnd=None; self.history=[]; self.state_lock=threading.Lock(); self.inject=False; self.last=None; self.listener=None
    self.pending=queue.Queue()
    self.root=tk.Tk(); self.root.title("My Switcher"); self.root.geometry("560x520")
    self.enabled=tk.BooleanVar(value=self.settings["enabled"]); self.startup=tk.BooleanVar(value=self.settings["startup"])
    f=ttk.Frame(self.root,padding=15); f.pack(fill="both",expand=True)
    ttk.Label(f,text="My Switcher",font=("Segoe UI",17,"bold")).pack(anchor="w")
    ttk.Label(f,text="Раскладка + орфография и грамматика · RU / UA / EN").pack(anchor="w",pady=(0,10))
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
    ttk.Button(f,text="Проверить текст (орфография и грамматика)",command=self.open_grammar).pack(anchor="w",pady=5)
    ttk.Separator(f).pack(fill="x",pady=10)
    ttk.Label(f,text="Раскладка обрабатывается локально. Проверка грамматики отправляет текст в LanguageTool.").pack(anchor="w",pady=3)
    ttk.Label(f,text="Грамматические исправления только предлагаются — текст не меняется автоматически.").pack(anchor="w")
    self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
    self.root.bind("<Unmap>", self.on_minimize)
    self.start_tray()
    self.start_listener()
    self.root.after(30, self.process_pending)
    self.root.mainloop()
 def start_tray(self):
    try:
      import pystray
      from PIL import Image, ImageDraw
      img=Image.new("RGB",(64,64),(35,75,130))
      d=ImageDraw.Draw(img); d.rounded_rectangle((3,3,61,61),radius=12,fill=(35,75,130))
      d.text((10,20),"MS",fill="white")
      menu=pystray.Menu(
        pystray.MenuItem("Открыть My Switcher", lambda icon,item:self.show_window(), default=True),
        pystray.MenuItem("Автоисправление вкл/выкл", lambda icon,item:self.root.after(0,self.toggle_enabled)),
        pystray.MenuItem("Выход", lambda icon,item:self.root.after(0,self.exit_app)))
      self.tray=pystray.Icon("MySwitcher",img,"My Switcher · RU / UA / EN",menu)
      threading.Thread(target=self.tray.run,daemon=True).start()
    except Exception as e:
      self.status.set("Ошибка системного трея: "+str(e))
 def hide_to_tray(self):
    self.root.withdraw()
 def on_minimize(self,event=None):
    if event is not None and event.widget is self.root:
      try:
        if self.root.state()=="iconic": self.root.after(100,self.root.withdraw)
      except Exception: pass
 def show_window(self):
    def show():
      self.root.deiconify(); self.root.state("normal"); self.root.lift(); self.root.focus_force()
    self.root.after(0,show)
 def toggle_enabled(self):
    self.enabled.set(not self.enabled.get()); self.save()
 def exit_app(self):
    try:
      if self.listener: self.listener.stop()
    except Exception: pass
    try:
      if getattr(self,"tray",None): self.tray.stop()
    except Exception: pass
    try: self.root.quit(); self.root.destroy()
    except Exception: pass
 def save(self):
    self.settings["enabled"]=self.enabled.get(); CONFIG.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding="utf-8")
 def set_startup(self):
    self.settings["startup"]=self.startup.get();self.save()
    try:
      import winreg
      key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run",0,winreg.KEY_SET_VALUE)
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
 def open_grammar(self):
    win=tk.Toplevel(self.root)
    win.title("Проверка орфографии и грамматики")
    win.geometry("720x600")
    win.transient(self.root)
    outer=ttk.Frame(win,padding=12); outer.pack(fill="both",expand=True)
    ttk.Label(outer,text="Вставьте текст для проверки. Он будет отправлен в LanguageTool (онлайн).",wraplength=680).pack(anchor="w",pady=(0,8))
    controls=ttk.Frame(outer); controls.pack(fill="x",pady=(0,8))
    ttk.Label(controls,text="Язык:").pack(side="left")
    lang=tk.StringVar(value="ru")
    ttk.Combobox(controls,textvariable=lang,values=("ru","ua","en"),state="readonly",width=8).pack(side="left",padx=6)
    text_box=tk.Text(outer,wrap="word",height=10,undo=True)
    text_box.pack(fill="both",expand=True)
    result_box=tk.Text(outer,wrap="word",height=9,state="disabled")
    result_box.pack(fill="both",expand=True,pady=(8,0))
    status=tk.StringVar(value="Проверка не запускалась.")
    ttk.Label(outer,textvariable=status).pack(anchor="w",pady=6)
    def run_check():
      value=text_box.get("1.0","end-1c")
      if not value.strip():
        status.set("Сначала введите или вставьте текст.")
        return
      selected_language=lang.get()
      check_btn.configure(state="disabled")
      status.set("Проверяем…")
      def worker():
        try:
          matches=check_text(value,selected_language)
          def show():
            result_box.configure(state="normal");result_box.delete("1.0","end")
            if not matches:
              result_box.insert("end","Ошибок по правилам LanguageTool не найдено.")
            else:
              for i,m in enumerate(matches,1):
                start=m["offset"]; end=start+m["length"]
                fragment=value[start:end]
                replacement=", ".join(m["replacements"]) if m["replacements"] else "нет предложений"
                result_box.insert("end",str(i)+". "+repr(fragment)+" — "+m["message"]+"\n   Варианты: "+replacement+"\n\n")
            result_box.configure(state="disabled")
            status.set("Проверка завершена. Найдено замечаний: "+str(len(matches))+".")
            check_btn.configure(state="normal")
          self.root.after(0,show)
        except GrammarServiceError as exc:
          message=str(exc)
          self.root.after(0,lambda message=message: (status.set(message),check_btn.configure(state="normal")))
        except Exception as exc:
          message="Ошибка проверки: "+str(exc)
          self.root.after(0,lambda message=message: (status.set(message),check_btn.configure(state="normal")))
      threading.Thread(target=worker,daemon=True).start()
    check_btn=ttk.Button(controls,text="Проверить",command=run_check)
    check_btn.pack(side="left",padx=8)
 def start_listener(self):
    try:
      from pynput import keyboard
      self.keyboard=keyboard; self.controller=keyboard.Controller()
      self.listener=keyboard.Listener(on_press=self.on_press,on_release=self.on_release);self.listener.daemon=True;self.listener.start()
      self.status.set("Работает локально · RU / UA / EN")
    except Exception as e:self.status.set("Ошибка клавиатурного модуля: "+str(e))
 def process_pending(self):
    try:
      while True:
        w, delimiter, target_hwnd, phrase = self.pending.get_nowait()
        self.correct_after_delimiter(w, delimiter, target_hwnd, phrase)
    except queue.Empty: pass
    except Exception as e: log_debug("pending queue exception: " + repr(e))
    try: self.root.after(30, self.process_pending)
    except Exception: pass
 def on_release(self,key):
    try:
      if self.keyboard and key == self.keyboard.Key.caps_lock:
        log_debug("physical CapsLock release; toggle_state=" + str(key_state(0x14)) + "; foreground=" + foreground_exe())
      elif self.keyboard and key in (self.keyboard.Key.shift,self.keyboard.Key.shift_l,self.keyboard.Key.shift_r):
        log_debug("physical Shift release; caps_lock=" + str(key_state(0x14)) + "; foreground=" + foreground_exe())
    except Exception as e:
      log_debug("on_release diagnostic exception: " + repr(e))
 def on_press(self,key):
    if self.keyboard and key == self.keyboard.Key.caps_lock:
      log_debug("physical CapsLock press; toggle_state=" + str(key_state(0x14)) + "; foreground=" + foreground_exe())
    elif self.keyboard and key in (self.keyboard.Key.shift,self.keyboard.Key.shift_l,self.keyboard.Key.shift_r):
      log_debug("physical Shift press; caps_lock=" + str(key_state(0x14)) + "; foreground=" + foreground_exe())
    if self.inject or not self.settings.get("enabled",True):return
    try:
      hwnd=foreground_window()
      if self.buffer and self.buffer_hwnd and hwnd != self.buffer_hwnd:
        self.buffer=""; self.history=[]
      self.buffer_hwnd=hwnd
      if key in (self.keyboard.Key.space, self.keyboard.Key.enter, self.keyboard.Key.tab):
        w=self.buffer
        self.buffer=""
        delimiter = key
        # A comma typed while the English layout is active may actually be the
        # Russian/Ukrainian letter "б" in a mistyped word (e.g. hf,jns -> работы).
        # If it is a trailing comma followed by a space, keep it as punctuation.
        if w.endswith(",") and key == self.keyboard.Key.space:
          w = w[:-1]
          delimiter = ", "
        if len(w)>=1 and foreground_exe() not in self.settings.get("excluded_apps",[]):
          with self.state_lock:
            phrase = " ".join((self.history + [w])[-5:])
            self.history = (self.history + [w])[-5:]
          self.pending.put((w, delimiter, hwnd, phrase))
        else:
          self.history = []
      elif key==self.keyboard.Key.backspace:self.buffer=self.buffer[:-1]; self.history=[]
      elif key in (self.keyboard.Key.shift,self.keyboard.Key.shift_l,self.keyboard.Key.shift_r,self.keyboard.Key.ctrl,self.keyboard.Key.ctrl_l,self.keyboard.Key.ctrl_r,self.keyboard.Key.alt,self.keyboard.Key.alt_l,self.keyboard.Key.alt_r):pass
      else:
        c=getattr(key,"char",None)
        if c and c.isalpha():self.buffer=(self.buffer+c)[-64:]
        elif c == "," and self.buffer and script_of(self.buffer) == "en":
          # Do not split a potentially mistyped Cyrillic word at the physical comma
          # key: on RU/UA layout that key produces "б".
          self.buffer = (self.buffer + c)[-64:]
        elif c in (".", ";", ":", "!", "?"):
          w=self.buffer
          self.buffer=""
          if len(w)>=1 and foreground_exe() not in self.settings.get("excluded_apps",[]):
            phrase = " ".join((self.history + [w])[-5:])
            self.pending.put((w, c, hwnd, phrase))
          self.history=[]
        elif c:self.buffer=""
    except Exception as e:
      log_debug("on_press exception: " + repr(e) + " " + traceback.format_exc())
 def correct_after_delimiter(self,w,delimiter,target_hwnd=None,phrase=None):
    if target_hwnd and foreground_window() != target_hwnd:
      log_debug("correction skipped because focus changed")
      return
    self.correct(w,delimiter,phrase or w)
 def correct(self,w,delimiter=None,phrase=None):
    phrase = phrase or w
    log_debug("phrase boundary received; text=" + repr(phrase) + "; words=" + str(len(phrase.split())) + "; foreground=" + foreground_exe())
    try:
      log_debug("phrase analysis: " + repr(get_engine().explain_phrase(phrase, self.words)))
    except Exception as e:
      log_debug("phrase analysis exception: " + repr(e))
    result = get_engine().suggest_phrase(phrase, self.words)
    if not result:
      log_debug("no confident phrase correction")
      return
    new_phrase, dst, score, current_score = result
    log_debug("confident phrase correction selected; target=" + dst + " score=" + str(score) + " current=" + str(current_score))
    if not self.replace_word(phrase, new_phrase, delimiter):
      log_debug("correction transaction failed; layout not changed")
      return
    with self.state_lock:
      self.history = new_phrase.split()[-5:] if delimiter == self.keyboard.Key.space else []
    activate_layout(dst)
 def replace_word(self, old, new, delimiter=None):
    self.inject=True
    caps_before=key_state(0x14)
    try:
      # Replace token and delimiter as one serialized transaction. Unicode
      # VK_PACKET input is independent of the active keyboard layout.
      delimiter_len = 1 if delimiter in (self.keyboard.Key.space, self.keyboard.Key.enter, self.keyboard.Key.tab) else len(delimiter) if isinstance(delimiter, str) else 0
      send_backspaces(len(old) + delimiter_len)
      send_unicode_text(new)
      if delimiter == self.keyboard.Key.space:self.controller.tap(self.keyboard.Key.space)
      elif delimiter == self.keyboard.Key.enter:self.controller.tap(self.keyboard.Key.enter)
      elif delimiter == self.keyboard.Key.tab:self.controller.tap(self.keyboard.Key.tab)
      elif isinstance(delimiter, str):send_unicode_text(delimiter)
      self.last=(old,new,delimiter,time.time())
      caps_after=key_state(0x14)
      log_debug("replacement injected; old_length=" + str(len(old)) + " new_length=" + str(len(new)) + "; caps_before=" + str(caps_before) + "; caps_after=" + str(caps_after) + "; foreground=" + foreground_exe())
      if caps_before != caps_after: log_debug("WARNING CapsLock state changed during replacement transaction")
      return True
    except Exception as e:
      log_debug("replace exception: " + repr(e) + " " + traceback.format_exc() + "; caps_before=" + str(caps_before) + "; caps_after=" + str(key_state(0x14)))
      return False
    finally:
      self.inject=False
 def undo(self):
    if not self.last or time.time()-self.last[3]>60:
      messagebox.showinfo("Отмена","Нет недавнего исправления");return
    old,new,delimiter,_=self.last;self.inject=True
    try:
      delimiter_len = 1 if delimiter in (self.keyboard.Key.space, self.keyboard.Key.enter, self.keyboard.Key.tab) else len(delimiter) if isinstance(delimiter, str) else 0
      send_backspaces(len(new)+delimiter_len)
      send_unicode_text(old)
      if delimiter == self.keyboard.Key.space:self.controller.tap(self.keyboard.Key.space)
      elif delimiter == self.keyboard.Key.enter:self.controller.tap(self.keyboard.Key.enter)
      elif delimiter == self.keyboard.Key.tab:self.controller.tap(self.keyboard.Key.tab)
      elif isinstance(delimiter,str):send_unicode_text(delimiter)
      self.last=None
    except Exception as e:
      log_debug("undo exception: " + repr(e) + " " + traceback.format_exc())
    finally:self.inject=False
if __name__=="__main__":
    if os.name!="nt":
        print("Windows 10/11 only")
    else:
        # Enforce a single running instance. Multiple keyboard listeners can
        # compete while replacing the same typed word and cause inconsistent results.
        _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        _kernel32.CreateMutexW.restype = ctypes.c_void_p
        _instance_mutex = _kernel32.CreateMutexW(None, True, "Local\\MySwitcher_SingleInstance")
        _already_running = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
        if _already_running:
            sys.exit(0)
        App()
