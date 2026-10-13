from __future__ import annotations
import json,shutil,threading,uuid
from copy import deepcopy
from pathlib import Path
from PySide6.QtWidgets import QApplication
from core.event_bus import EventBus
from core.logger import setup_logger
from core.permissions import PermissionManager
from core.approvals import PermissionMode
from core.task_manager import Task,TaskStatus
from core.tool_registry import ToolRegistry
from core.agent_loop import AgentLoop
from models.model_manager import ModelManager
from tools.files import FileTools
from tools.folders import FolderTools
from tools.commands import CommandTools
from tools.time_info import get_time
from tools.clipboard import read_clipboard,write_clipboard
from tools.programs import open_path,run_program,stop_program,list_programs
from tools.project_tools import scan_project,review_project,run_project_tests,git_status
from tools.extensions import list_extensions,read_extension
from tools.calculator import calculate_expression,convert_units
from computer_use.computer import ComputerController
from browser.browser_manager import BrowserManager
from relay_server import LocalRelayServer
from security.secret_store import is_protected, protect_secret, unprotect_secret
from ui.main_window import MainWindow

ROOT=Path(__file__).resolve().parent; CONFIG=ROOT/"config.json"
DEFAULTS={"provider":"ollama","ollama_base_url":"http://127.0.0.1:11434","base_url":"","api_key":"","model":"llama3.1:8b","vision_model":"","temperature":0.2,"reasoning_effort":None,"permission_mode":"ask_risky","workspace":str(ROOT/"workspace"),"max_steps":None,"model_timeout":None,"computer_use":{"enabled":True},"browser":{"profile":str(ROOT/"data"/"browser_profile")},"relay":{"enabled":False,"host":"127.0.0.1","port":8765,"auth_token":""}}
def load_config():
    try:
        raw=json.loads(CONFIG.read_text(encoding="utf-8"))
        data={**DEFAULTS,**raw}
        data["api_key"]=unprotect_secret(data.get("api_key",""))
        relay={**DEFAULTS["relay"],**data.get("relay",{})}
        relay["auth_token"]=unprotect_secret(relay.get("auth_token",""))
        data["relay"]=relay
        if ((raw.get("api_key") and not is_protected(raw.get("api_key"))) or
                (raw.get("relay",{}).get("auth_token") and not is_protected(raw.get("relay",{}).get("auth_token")))):
            CONFIG.write_text(json.dumps(_protected_config(data),ensure_ascii=False,indent=2),encoding="utf-8")
        return data
    except Exception:
        if CONFIG.exists(): shutil.copy2(CONFIG,CONFIG.with_suffix(".broken.json"))
        CONFIG.write_text(json.dumps(DEFAULTS,ensure_ascii=False,indent=2),encoding="utf-8"); return dict(DEFAULTS)
def _protected_config(config):
    stored=deepcopy(config)
    stored["api_key"]=protect_secret(stored.get("api_key",""))
    stored.setdefault("relay",{})["auth_token"]=protect_secret(stored.get("relay",{}).get("auth_token",""))
    return stored
def obj(properties=None,required=None): return {"type":"object","properties":properties or {},**({"required":required} if required else {})}
def prop(kind,description): return {"type":kind,"description":description}

class App:
    def __init__(self):
        self.config=load_config(); self.events=EventBus(); self.logger=setup_logger(ROOT/"logs"); self.model_manager=ModelManager(self.config); self.permissions=PermissionManager(self.config.get("permission_mode","ask_risky")); self.computer=ComputerController(self.permissions); self.browser=BrowserManager(self.config.get("browser",{}).get("profile")); relay=self.config.get("relay",{}); self.relay=LocalRelayServer(self.config.get("base_url",""),self.config.get("api_key",""),relay.get("host","127.0.0.1"),relay.get("port",8765),relay.get("auth_token","")); self.registry=ToolRegistry(); self.background_tasks={}; self.background_threads={}; self.task_lock=threading.Lock(); self._register_tools(); self.loop=AgentLoop(self.model_manager,self.registry,self.permissions,self.logger,self.events,self.config.get("max_steps",30)); self.logger.info("[ToolCheck] %s",self.registry.self_check()); self.apply_relay_config()
    def _register_tools(self):
        r=self.registry.register; files=FileTools(self.config["workspace"]); folders=FolderTools(self.config["workspace"]); self.command_tools=CommandTools(); commands=self.command_tools; shot=str(ROOT/"screenshots"/"latest.png"); bshot=str(ROOT/"screenshots"/"browser.png")
        path=prop("string","Windows 路径；相对路径基于 workspace，绝对路径保持原样")
        r("read_file",files.read_file,"读取文本文件并返回内容、路径和大小。",obj({"path":path},["path"]),"FILES")
        r("write_file",files.write_file,"创建或覆盖文本文件，实际写入 UTF-8 内容。",obj({"path":path,"content":prop("string","完整文件内容"),"overwrite":prop("boolean","是否允许覆盖")},["path","content"]),"FILES","high")
        r("append_file",files.append_file,"向文本文件追加 UTF-8 内容。",obj({"path":path,"content":prop("string","追加内容")},["path","content"]),"FILES","high")
        for name,fn,desc in [("copy_file",files.copy_file,"复制文件"),("move_file",files.move_file,"移动文件")]: r(name,fn,desc,obj({"source":path,"destination":path},["source","destination"]),"FILES","high")
        r("rename_file",files.rename_file,"重命名文件。",obj({"path":path,"new_name":prop("string","新文件名")},["path","new_name"]),"FILES","high")
        r("delete_file",files.delete_file,"删除指定普通文件。",obj({"path":path},["path"]),"FILES","critical")
        r("file_info",files.file_info,"获取文件大小和修改时间。",obj({"path":path},["path"]),"FILES")
        r("search_files",files.search_files,"按名称递归搜索文件或文件夹。",obj({"query":prop("string","名称关键字"),"path":path},["query"]),"FILES")
        r("create_folder",folders.create_folder,"创建文件夹和缺失的父目录。桌面路径请使用“桌面\\文件夹名”或“Desktop\\文件夹名”，不要猜 Windows 用户名。",obj({"path":path},["path"]),"FILES","high")
        r("list_folder",folders.list_folder,"列出目录中的真实文件和文件夹。",obj({"path":path}),"FILES")
        for name,fn,desc in [("copy_folder",folders.copy_folder,"复制文件夹"),("move_folder",folders.move_folder,"移动文件夹")]: r(name,fn,desc,obj({"source":path,"destination":path},["source","destination"]),"FILES","high")
        r("rename_folder",folders.rename_folder,"重命名文件夹。",obj({"path":path,"new_name":prop("string","新名称")},["path","new_name"]),"FILES","high")
        r("delete_folder",folders.delete_folder,"递归删除文件夹。",obj({"path":path},["path"]),"FILES","critical")
        r("run_powershell",lambda command,timeout=None:commands.run_command(command,"powershell",timeout),"执行 PowerShell 并返回 stdout、stderr、exit_code。默认不设时间限制，直到命令完成或用户手动停止。",obj({"command":prop("string","PowerShell 命令"),"timeout":prop("integer","可选超时秒数；不提供则无限等待")},["command"]),"TERMINAL","high")
        r("run_cmd",lambda command,timeout=None:commands.run_command(command,"cmd",timeout),"执行 CMD 并返回 stdout、stderr、exit_code。默认不设时间限制，直到命令完成或用户手动停止。",obj({"command":prop("string","CMD 命令"),"timeout":prop("integer","可选超时秒数；不提供则无限等待")},["command"]),"TERMINAL","high")
        r("cmd",lambda c="",command="",timeout=None:commands.run_command(c or command,"cmd",timeout),"兼容模型输出的 cmd 工具别名；执行后返回真实退出码。",obj({"c":prop("string","CMD 命令"),"command":prop("string","CMD 命令"),"timeout":prop("integer","可选超时秒数；不提供则无限等待")},[]),"TERMINAL","high")
        r("run_program",run_program,"启动 Windows 程序，参数使用数组，返回 PID。",obj({"program":prop("string","exe 或程序路径"),"args":{"type":"array","items":{"type":"string"}},"working_directory":path},["program"]),"PROGRAM","high")
        r("stop_program",stop_program,"终止由用户授权的指定 PID。",obj({"pid":prop("integer","进程 PID")},["pid"]),"PROGRAM","high")
        r("list_programs",list_programs,"列出当前进程。",obj(),"PROGRAM")
        r("open_path",open_path,"使用 Windows 默认程序打开文件或文件夹。",obj({"path":path},["path"]),"PROGRAM","high")
        r("open_computer",lambda:open_path("shell:MyComputerFolder"),"打开 Windows 的“此电脑/我的电脑/Computer/PC”窗口。用户说打开电脑、打开 PC、打开此电脑、打开文件管理器时都使用此工具。",obj(),"PROGRAM","high")
        project_path=prop("string","项目目录的绝对路径或相对 workspace 路径")
        r("scan_project",scan_project,"扫描项目结构、语言、清单文件和 Python 类/函数，帮助 Agent 理解整个代码项目。",obj({"path":project_path,"max_files":prop("integer","最多扫描文件数")}),"PROJECT")
        r("review_project",review_project,"执行静态代码审查，检查 Python 语法错误、TODO/FIXME 和 Git diff 问题。",obj({"path":project_path}),"REVIEW")
        r("run_project_tests",run_project_tests,"运行项目测试并进行 Python 编译检查，返回完整退出码和日志。",obj({"path":project_path}),"REVIEW","high")
        r("git_status",git_status,"查看项目 Git 改动状态。",obj({"path":project_path}),"PROJECT")
        r("list_extensions",list_extensions,"发现本地 extensions、Skills 和 Codex skills。",obj(),"EXTENSIONS")
        r("read_extension",read_extension,"读取指定本地 Skill 或扩展的说明和 manifest。",obj({"name":prop("string","扩展名称")},["name"]),"EXTENSIONS")
        r("start_background_task",self.start_background_task,"把长时间任务放到后台继续执行，立即返回 task_id。",obj({"text":prop("string","要执行的完整任务")},["text"]),"PROJECT","high")
        r("list_background_tasks",self.list_background_tasks,"查看后台任务的状态、步骤和结果。",obj(),"PROJECT")
        r("stop_background_task",self.stop_background_task,"停止指定后台任务。",obj({"task_id":prop("string","后台任务 ID")},["task_id"]),"PROJECT","high")
        r("get_time",get_time,"读取本机当前日期、时间和时区。",obj(),"SYSTEM")
        r("calculate_expression",calculate_expression,"本地安全计算器：支持四则运算、幂、百分比和常用数学函数，不调用模型。",obj({"expression":prop("string","数学表达式")},["expression"]),"SYSTEM")
        r("convert_units",convert_units,"本地单位换算：长度、质量、时间和速度。",obj({"value":prop("number","数值"),"from_unit":prop("string","原单位"),"to_unit":prop("string","目标单位"),"category":prop("string","类别，可选")},["value","from_unit","to_unit"]),"SYSTEM")
        r("clipboard_read",lambda:{"success":True,"text":read_clipboard()},"读取当前剪贴板文本。",obj(),"CLIPBOARD","high"); r("clipboard_write",write_clipboard,"写入剪贴板文本。",obj({"text":prop("string","要写入的文本")},["text"]),"CLIPBOARD","high")
        c=self.computer
        r("take_screenshot",lambda path=shot,region=None:c.screenshot(path,region),"获取真实桌面截图；可指定 [x,y,width,height] 区域。",obj({"path":path,"region":{"type":"array","items":{"type":"integer"}}}),"COMPUTER")
        r("computer_get_screen_size",c.screen_size,"读取 DPI 感知后的屏幕尺寸。",obj(),"COMPUTER"); r("computer_get_mouse_position",c.mouse_position,"读取当前鼠标绝对坐标。",obj(),"COMPUTER")
        r("computer_move_mouse",c.move_mouse,"移动鼠标到屏幕绝对坐标。",obj({"x":prop("integer","绝对 X 坐标"),"y":prop("integer","绝对 Y 坐标"),"duration":prop("number","移动秒数")},["x","y"]),"COMPUTER","high")
        r("computer_click",c.click,"在 Windows 桌面指定坐标点击；网页优先 browser_click。",obj({"x":prop("integer","绝对 X 坐标"),"y":prop("integer","绝对 Y 坐标"),"button":prop("string","left/right/middle"),"clicks":prop("integer","点击次数")}),"COMPUTER","high")
        r("computer_double_click",c.double_click,"双击屏幕坐标。",obj({"x":prop("integer","X"),"y":prop("integer","Y")}),"COMPUTER","high"); r("computer_right_click",c.right_click,"右击屏幕坐标。",obj({"x":prop("integer","X"),"y":prop("integer","Y")}),"COMPUTER","high")
        r("computer_drag",c.drag,"拖拽到指定屏幕坐标。",obj({"x":prop("integer","X"),"y":prop("integer","Y"),"duration":prop("number","秒")},["x","y"]),"COMPUTER","high"); r("computer_scroll",c.scroll,"滚动鼠标滚轮。",obj({"amount":prop("integer","正数向上，负数向下")},["amount"]),"COMPUTER","high")
        r("computer_type_text",c.type_text,"向当前已激活窗口输入文本。",obj({"text":prop("string","输入文本"),"interval":prop("number","字符间隔")},["text"]),"COMPUTER","high"); r("computer_press_key",c.press_key,"按一个键。",obj({"key":prop("string","如 enter、esc、tab")},["key"]),"COMPUTER","high"); r("computer_hotkey",c.hotkey,"执行组合快捷键。",obj({"keys":{"type":"array","items":{"type":"string"},"description":"如 [ctrl,s]"}},["keys"]),"COMPUTER","high")
        r("computer_list_windows",c.list_windows,"列出桌面窗口及其位置。",obj(),"COMPUTER"); r("computer_get_active_window",c.active_window,"读取当前活动窗口。",obj(),"COMPUTER"); r("computer_activate_window",c.activate_window,"按标题激活目标窗口后再输入。",obj({"title":prop("string","窗口标题关键字")},["title"]),"COMPUTER","high")
        for action in ("minimize","maximize","restore"): r("computer_"+action+"_window",lambda title,a=action:c.window_action(title,a),action+" 窗口。",obj({"title":prop("string","窗口标题")},["title"]),"COMPUTER","high")
        b=self.browser
        r("browser_open",b.open,"用 Playwright 打开浏览器并访问 URL；支持登录页面，使用独立本地配置目录。",obj({"url":prop("string","完整 URL"),"headless":prop("boolean","是否无界面")}),"BROWSER","high")
        r("browser_navigate",b.navigate,"导航到 URL。",obj({"url":prop("string","完整 URL")},["url"]),"BROWSER"); r("browser_click",b.click,"通过 CSS 或文本 selector 点击网页元素。",obj({"selector":prop("string","Playwright selector")},["selector"]),"BROWSER","high")
        r("browser_type",b.type,"向网页输入框填入文字。",obj({"selector":prop("string","selector"),"text":prop("string","文字"),"press_enter":prop("boolean","是否回车")},["selector","text"]),"BROWSER","high"); r("browser_read_page",b.read_page,"读取网页标题、URL 和正文。",obj(),"BROWSER")
        r("browser_scroll",b.scroll,"滚动网页。",obj({"amount":prop("integer","滚动量")}),"BROWSER"); r("browser_screenshot",lambda path=bshot:b.screenshot(path),"保存网页截图。",obj({"path":path}),"BROWSER")
        for name,fn in [("browser_back",b.back),("browser_forward",b.forward),("browser_refresh",b.refresh),("browser_close",b.close)]: r(name,fn,name.replace("browser_","")+" browser",obj(),"BROWSER")
    def status_text(self): return f"Agent Ready · Ollama {'Connected' if self.model_manager.online() else 'Offline'} · Computer Use {'Ready' if self.computer.status()['ready'] else 'Stopped'} · 模型 {self.model_manager.active_model() or '未选择'}"
    def model_text(self): return json.dumps({"provider":self.model_manager.provider_name,"online":self.model_manager.online(),"model":self.model_manager.active_model(),"models":self.model_manager.models,"capabilities":self.model_manager.capabilities()},ensure_ascii=False,indent=2)
    def save_config(self): CONFIG.write_text(json.dumps(_protected_config(self.config),ensure_ascii=False,indent=2),encoding="utf-8")
    def apply_relay_config(self):
        relay=self.config.setdefault("relay",dict(DEFAULTS["relay"])); self.relay.configure(self.config.get("base_url",""),self.config.get("api_key",""),relay.get("host","127.0.0.1"),relay.get("port",8765),relay.get("auth_token",""))
        if not relay.get("enabled"):
            return self.relay.stop()
        if self.config.get("provider") == "ollama":
            return {"success":False,"running":False,"error":"本地中转站当前需要 OpenAI-compatible 上游；请先选择 DeepSeek 或其他 API"}
        result=self.relay.start(); self.logger.info("[Relay] %s",result); return result
    def stop_relay(self): return self.relay.stop()
    def cancel_tools(self):
        result=self.command_tools.cancel_all()
        try: self.browser.close()
        except Exception: pass
        return result
    def set_permission_mode(self,mode): self.permissions.set_mode(mode); self.config["permission_mode"]=mode.value if hasattr(mode,"value") else str(mode); self.save_config()
    def set_model(self,model,source=None):
        if source: self.model_manager.set_model_choice(model,source)
        else: self.model_manager.set_model(model)
        self.save_config()
    def set_vision_model(self,model): self.model_manager.set_vision_model(model); self.save_config()
    def start_background_task(self,text):
        task=Task(text); task.id="bg_"+uuid.uuid4().hex[:10]
        with self.task_lock: self.background_tasks[task.id]=task
        def runner():
            try: task.result=self.loop.run(task,[])
            except Exception as exc: task.status=TaskStatus.FAILED; task.error=str(exc); self.logger.exception("[BackgroundTask] %s",task.id)
        thread=threading.Thread(target=runner,name=task.id,daemon=True); self.background_threads[task.id]=thread; thread.start()
        return {"success":True,"task_id":task.id,"status":task.status.value}
    def list_background_tasks(self):
        with self.task_lock:
            return {"success":True,"tasks":[{"task_id":k,"text":v.text,"status":v.status.value,"step":v.step,"result":v.result[-1000:]} for k,v in self.background_tasks.items()]}
    def stop_background_task(self,task_id):
        task=self.background_tasks.get(task_id)
        if not task: return {"success":False,"error":"后台任务不存在","task_id":task_id}
        task.stop(); return {"success":True,"task_id":task_id,"status":task.status.value}
def main():
    qt=QApplication([]); qt.setApplicationName("本地 Agent"); app=App(); window=MainWindow(app); window.show(); return qt.exec()
if __name__=="__main__": raise SystemExit(main())
